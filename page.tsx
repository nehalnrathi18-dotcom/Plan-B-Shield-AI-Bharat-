
"use client";
import { useState } from "react";

export default function Home() {

  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<any[]>([]);
  const [history, setHistory] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const generate = async () => {

    if (!prompt) return;

    const userPrompt = prompt;

    setMessages(prev => [...prev, { role: "user", text: userPrompt }]);
    setHistory(prev => [userPrompt, ...prev]);
    setPrompt("");
    setLoading(true);

    try {

      const res = await fetch(process.env.NEXT_PUBLIC_API_URL!, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt: userPrompt }),
      });

      const data = await res.json();

      if (res.status === 403) {

        setMessages(prev => [
          ...prev,
          { role: "ai", error: "Blocked: " + data.reason }
        ]);

        return;
      }

      if (!res.ok) {

        setMessages(prev => [
          ...prev,
          { role: "ai", error: "Server error occurred" }
        ]);

        return;
      }

      setMessages(prev => [
        ...prev,
        {
          role: "ai",
          image: data.image_url,
          status: data.classification
        }
      ]);

    } catch (error) {

      setMessages(prev => [
        ...prev,
        { role: "ai", error: "Something went wrong" }
      ]);

    } finally {

      setLoading(false);

    }

  };

  return (

    <div style={{
      display: "flex",
      height: "100vh",
      background: "#0f172a",
      color: "white",
      fontFamily: "Arial"
    }}>

      {/* SIDEBAR */}

      <div style={{
        width: "260px",
        background: "#020617",
        borderRight: "1px solid #1e293b",
        padding: "20px",
        overflowY: "auto"
      }}>

        <h2 style={{marginBottom:"20px"}}>ShieldAI</h2>

        <p style={{fontSize:"12px",opacity:0.6}}>
          Prompt History
        </p>

        {history.map((item,index)=>(
          <div
            key={index}
            style={{
              marginTop:"10px",
              padding:"10px",
              background:"#1e293b",
              borderRadius:"6px",
              fontSize:"13px"
            }}
          >
            {item}
          </div>
        ))}

      </div>


      {/* MAIN PANEL */}

      <div style={{
        flex:1,
        display:"flex",
        flexDirection:"column"
      }}>

        {/* HEADER */}

        <div style={{
          padding:"20px",
          borderBottom:"1px solid #334155",
          textAlign:"center",
          fontSize:"22px",
          fontWeight:"bold"
        }}>
          ShieldAI Bharat – Safe AI Image Generator
        </div>


        {/* CHAT AREA */}

        <div style={{
          flex:1,
          overflowY:"auto",
          padding:"30px",
          maxWidth:"900px",
          margin:"auto",
          width:"100%"
        }}>

          {messages.map((msg,index)=>(

            <div key={index} style={{marginBottom:"25px"}}>

              {msg.role==="user" && (

                <div style={{
                  background:"#2563eb",
                  padding:"12px",
                  borderRadius:"10px",
                  maxWidth:"70%",
                  marginLeft:"auto"
                }}>
                  {msg.text}
                </div>

              )}

              {msg.role==="ai" && (

                <div style={{
                  background:"#1e293b",
                  padding:"15px",
                  borderRadius:"10px",
                  maxWidth:"70%"
                }}>

                  {msg.image && (
                    <>
                      <img
                        src={msg.image}
                        width="420"
                        style={{
                          borderRadius:"10px",
                          marginBottom:"10px"
                        }}
                      />

                      <p style={{fontSize:"13px",opacity:0.8}}>
                        Status: {msg.status}
                      </p>

                      <a href={msg.image} download>
                        <button style={{
                          marginTop:"8px",
                          padding:"8px 15px",
                          background:"#22c55e",
                          border:"none",
                          borderRadius:"6px",
                          color:"white",
                          cursor:"pointer"
                        }}>
                          Download Image
                        </button>
                      </a>
                    </>
                  )}

                  {msg.error && (
                    <span style={{color:"#f87171"}}>
                      {msg.error}
                    </span>
                  )}

                </div>

              )}

            </div>

          ))}

          {loading && (
            <p>Generating AI image...</p>
          )}

        </div>


        {/* INPUT AREA */}

        <div style={{
          padding:"20px",
          borderTop:"1px solid #334155"
        }}>

          <div style={{
            maxWidth:"900px",
            margin:"auto",
            display:"flex",
            gap:"10px"
          }}>

            <input
              value={prompt}
              onChange={(e)=>setPrompt(e.target.value)}
              placeholder="Ask ShieldAI to generate an image..."
              style={{
                flex:1,
                padding:"12px",
                borderRadius:"8px",
                border:"none"
              }}
            />

            <button
              onClick={generate}
              style={{
                padding:"12px 20px",
                background:"#3b82f6",
                border:"none",
                borderRadius:"8px",
                color:"white",
                cursor:"pointer"
              }}
            >
              Generate
            </button>

          </div>

        </div>

      </div>

    </div>

  );

}
