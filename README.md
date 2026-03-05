# ShieldAI Bharat

AI Image Generator with Safety Moderation built using AWS.

## Problem
AI image generators can sometimes produce unsafe or harmful images.

## Solution
ShieldAI Bharat adds safety checks before and after image generation.

## Architecture

User → Next.js Frontend  
→ API Gateway  
→ AWS Lambda  
→ Amazon Bedrock (Nova Lite)  
→ Titan Image Generator  
→ Amazon Rekognition  
→ Amazon S3  
→ DynamoDB  

## Tech Stack

Frontend  
Next.js

Backend  
AWS Lambda

AI Models  
Amazon Bedrock (Nova Lite, Titan Image Generator)

Moderation  
Amazon Rekognition

Storage  
Amazon S3

Database  
Amazon DynamoDB

## Live Demo

(Add your Vercel link here)
