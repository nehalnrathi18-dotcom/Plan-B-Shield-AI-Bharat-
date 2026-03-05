
import json
import base64
import os
import logging
import re
from datetime import datetime
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from botocore.client import Config

# ---------------------------------------------------
# Configuration
# ---------------------------------------------------

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TEXT_REGION = os.environ.get("TEXT_REGION", "us-east-1").strip()
IMAGE_REGION = os.environ.get("IMAGE_REGION", "us-east-1").strip()

S3_BUCKET = os.environ.get("S3_BUCKET")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE")
IMAGE_MODEL_ID = os.environ.get("IMAGE_MODEL_ID")
TEXT_MODEL_ID = os.environ.get("TEXT_MODEL_ID")

# Bedrock clients (us-east-1)
bedrock_text = boto3.client("bedrock-runtime", region_name=TEXT_REGION)
bedrock_image = boto3.client("bedrock-runtime", region_name=IMAGE_REGION)

# Rekognition (Mumbai works fine)
rekognition = boto3.client("rekognition", region_name="ap-south-1")

# S3 client must match bucket region
s3 = boto3.client(
    "s3",
    region_name="ap-south-1",
    config=Config(signature_version="s3v4")
)

# DynamoDB
dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(DYNAMODB_TABLE)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "OPTIONS,POST",
    "Access-Control-Allow-Headers": "Content-Type",
}

# ---------------------------------------------------
# Helper Response
# ---------------------------------------------------

def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }

# ---------------------------------------------------
# TEXT CLASSIFICATION (Nova Lite)
# ---------------------------------------------------

def classify_prompt(prompt: str):

    system_prompt = """
You are an AI safety classifier.

Classify the following user prompt as SAFE or UNSAFE.
If unsafe, explain briefly why.

Return ONLY raw JSON.
Format:
{"classification":"SAFE|UNSAFE","reason":"string"}
"""

    full_prompt = f"{system_prompt}\n\nUser Prompt:\n{prompt}"

    model_response = bedrock_text.converse(
        modelId=TEXT_MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [{"text": full_prompt}]
            }
        ],
        inferenceConfig={
            "maxTokens": 300,
            "temperature": 0,
            "topP": 1
        }
    )

    output_text = model_response["output"]["message"]["content"][0]["text"].strip()
    logger.info(f"Nova raw response: {output_text}")

    cleaned = re.sub(r"```json|```", "", output_text).strip()
    parsed = json.loads(cleaned)

    return parsed


# ---------------------------------------------------
# IMAGE GENERATION (Titan)
# ---------------------------------------------------

def generate_image(prompt: str):

    payload = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": prompt
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "height": 1024,
            "width": 1024,
            "cfgScale": 8.0
        }
    }

    model_response = bedrock_image.invoke_model(
        modelId=IMAGE_MODEL_ID,
        body=json.dumps(payload),
        contentType="application/json",
        accept="application/json"
    )

    raw_body = model_response["body"].read().decode("utf-8")
    parsed = json.loads(raw_body)

    logger.info("Titan image generated successfully")

    return parsed["images"][0]


# ---------------------------------------------------
# IMAGE MODERATION (Rekognition)
# ---------------------------------------------------

def moderate_image(image_bytes: bytes):

    moderation = rekognition.detect_moderation_labels(
        Image={"Bytes": image_bytes}
    )

    blocked_categories = ["Explicit Nudity", "Sexual Content", "Violence"]

    for label in moderation.get("ModerationLabels", []):
        if label["Name"] in blocked_categories and label["Confidence"] > 70:
            return False

    return True


# ---------------------------------------------------
# DynamoDB Logging
# ---------------------------------------------------

def log_request(data: dict):
    try:
        table.put_item(Item=data)
    except Exception as e:
        logger.error(f"DynamoDB logging failed: {str(e)}")


# ---------------------------------------------------
# Lambda Handler
# ---------------------------------------------------

def lambda_handler(event, context):

    try:

        if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
            return response(200, {})

        method = event.get("requestContext", {}).get("http", {}).get("method")

        if method != "POST":
            return response(400, {"error": "Method not allowed"})

        body = json.loads(event.get("body") or "{}")
        prompt = body.get("prompt", "").strip()

        if not prompt:
            return response(400, {"error": "Prompt is required"})

        request_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()

        # 1️⃣ Prompt Safety Check
        classification_result = classify_prompt(prompt)
        classification = classification_result.get("classification")
        reason = classification_result.get("reason", "")

        if classification != "SAFE":

            log_request({
                "request_id": request_id,
                "timestamp": timestamp,
                "prompt": prompt,
                "classification": classification,
                "classification_reason": reason,
                "status": "BLOCKED"
            })

            return response(403, {
                "status": "blocked",
                "reason": reason,
                "request_id": request_id
            })

        # 2️⃣ Generate Image
        image_base64 = generate_image(prompt)
        image_bytes = base64.b64decode(image_base64)

        # 3️⃣ Image Moderation
        if not moderate_image(image_bytes):

            log_request({
                "request_id": request_id,
                "timestamp": timestamp,
                "prompt": prompt,
                "classification": classification,
                "status": "BLOCKED_BY_REKOGNITION"
            })

            return response(403, {
                "status": "blocked",
                "reason": "Generated image failed moderation",
                "request_id": request_id
            })

        # 4️⃣ Upload to S3
        s3_key = f"images/{request_id}.png"

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=image_bytes,
            ContentType="image/png"
        )

        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": s3_key},
            ExpiresIn=3600
        )

        # 5️⃣ Log success
        log_request({
            "request_id": request_id,
            "timestamp": timestamp,
            "prompt": prompt,
            "classification": classification,
            "image_s3_key": s3_key,
            "status": "SUCCESS"
        })

        return response(200, {
            "status": "success",
            "image_url": presigned_url,
            "request_id": request_id,
            "classification": classification
        })

    except ClientError as e:
        logger.error(f"AWS Service Error: {str(e)}")
        return response(500, {"error": "AWS service error"})

    except Exception as e:
        logger.error(f"Internal Error: {str(e)}")
        return response(500, {"error": "Internal server error"})
````
