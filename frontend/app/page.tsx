"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [topic, setTopic] = useState("");
  const [language, setLanguage] = useState("tr");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, language }),
      });
      if (!res.ok) throw new Error("İstek başarısız");
      const data = await res.json();
      router.push(`/jobs/${data.id}`);
    } catch {
      setError("Bir hata oluştu. Backend çalışıyor mu?");
      setLoading(false);
    }
  };

  return (
    <main style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      padding: "2rem",
      background: "var(--bg-primary)",
      position: "relative",
      overflow: "hidden",
    }}>
      {/* Arka plan efekti */}
      <div style={{
        position: "absolute",
        width: "600px",
        height: "600px",
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(245,158,11,0.04) 0%, transparent 70%)",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        pointerEvents: "none",
      }} />

      {/* Logo / Başlık */}
      <div style={{ textAlign: "center", marginBottom: "3rem" }}>
        <div style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "10px",
          marginBottom: "1rem",
        }}>
          <div style={{
            width: "36px",
            height: "36px",
            borderRadius: "10px",
            background: "var(--accent)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "18px",
          }}>▶</div>
          <span style={{
            fontFamily: "var(--font-display)",
            fontSize: "22px",
            fontWeight: "700",
            color: "var(--text-primary)",
            letterSpacing: "-0.5px",
          }}>PhotoStory</span>
        </div>
        <h1 style={{
          fontFamily: "var(--font-display)",
          fontSize: "clamp(2rem, 5vw, 3.5rem)",
          fontWeight: "700",
          lineHeight: "1.1",
          letterSpacing: "-1.5px",
          marginBottom: "1rem",
          background: "linear-gradient(135deg, #f0f0f5 0%, #8888a0 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}>
          Bir konu ver,<br />video üretelim.
        </h1>
        <p style={{
          color: "var(--text-secondary)",
          fontSize: "16px",
          fontWeight: "400",
          lineHeight: "1.6",
        }}>
          Yapay zeka ile senaryo, ses, görsel ve video — otomatik.
        </p>
      </div>

      {/* Form kartı */}
      <div style={{
        width: "100%",
        maxWidth: "560px",
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "20px",
        padding: "2rem",
        position: "relative",
      }}>
        {/* Konu input */}
        <div style={{ marginBottom: "1.25rem" }}>
          <label style={{
            display: "block",
            fontSize: "12px",
            fontWeight: "500",
            color: "var(--text-secondary)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: "8px",
          }}>Konu</label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder="örn. Mars kolonisi, Osmanlı tarihi..."
            style={{
              width: "100%",
              padding: "14px 16px",
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              borderRadius: "12px",
              color: "var(--text-primary)",
              fontSize: "15px",
              fontFamily: "var(--font-body)",
              outline: "none",
              transition: "border-color 0.2s",
            }}
            onFocus={(e) => e.target.style.borderColor = "var(--border-accent)"}
            onBlur={(e) => e.target.style.borderColor = "var(--border)"}
          />
        </div>

        {/* Dil seçimi */}
        <div style={{ marginBottom: "1.75rem" }}>
          <label style={{
            display: "block",
            fontSize: "12px",
            fontWeight: "500",
            color: "var(--text-secondary)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: "8px",
          }}>Dil</label>
          <div style={{ display: "flex", gap: "8px" }}>
            {[{ value: "tr", label: "Türkçe" }, { value: "en", label: "English" }].map((lang) => (
              <button
                key={lang.value}
                onClick={() => setLanguage(lang.value)}
                style={{
                  flex: 1,
                  padding: "10px",
                  borderRadius: "10px",
                  border: language === lang.value ? "1px solid var(--border-accent)" : "1px solid var(--border)",
                  background: language === lang.value ? "var(--accent-glow)" : "var(--bg-secondary)",
                  color: language === lang.value ? "var(--accent)" : "var(--text-secondary)",
                  fontSize: "14px",
                  fontWeight: "500",
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
              >
                {lang.label}
              </button>
            ))}
          </div>
        </div>

        {/* Submit butonu */}
        <button
          onClick={handleSubmit}
          disabled={loading || !topic.trim()}
          style={{
            width: "100%",
            padding: "15px",
            borderRadius: "12px",
            border: "none",
            background: loading || !topic.trim() ? "var(--text-muted)" : "var(--accent)",
            color: loading || !topic.trim() ? "var(--text-secondary)" : "#000",
            fontSize: "15px",
            fontWeight: "600",
            fontFamily: "var(--font-display)",
            cursor: loading || !topic.trim() ? "not-allowed" : "pointer",
            transition: "all 0.2s",
            letterSpacing: "-0.2px",
          }}
        >
          {loading ? "Oluşturuluyor..." : "Video Üret →"}
        </button>

        {error && (
          <p style={{ color: "var(--error)", fontSize: "13px", textAlign: "center", marginTop: "12px" }}>
            {error}
          </p>
        )}
      </div>

      {/* Pipeline adımları */}
      <div style={{
        display: "flex",
        gap: "8px",
        marginTop: "2.5rem",
        flexWrap: "wrap",
        justifyContent: "center",
      }}>
        {["Senaryo", "Seslendirme", "Görseller", "Video"].map((step, i) => (
          <div key={step} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{
              padding: "6px 14px",
              borderRadius: "100px",
              border: "1px solid var(--border)",
              background: "var(--bg-card)",
              color: "var(--text-secondary)",
              fontSize: "12px",
              fontWeight: "500",
            }}>{step}</span>
            {i < 3 && <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>→</span>}
          </div>
        ))}
      </div>
    </main>
  );
}
