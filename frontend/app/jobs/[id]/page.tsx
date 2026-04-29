"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STEPS = [
  { key: "text", label: "Senaryo yazılıyor" },
  { key: "audio", label: "Seslendiriliyor" },
  { key: "images", label: "Görseller üretiliyor" },
  { key: "video", label: "Video oluşturuluyor" },
];

async function fetchJob(id: string) {
  const res = await fetch(`${API_URL}/api/jobs/${id}`);
  if (!res.ok) throw new Error("Job bulunamadı");
  return res.json();
}

async function fetchFiles(id: string) {
  const res = await fetch(`${API_URL}/api/jobs/${id}/files`);
  if (!res.ok) return null;
  return res.json();
}

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: job, isLoading, isError } = useQuery({
    queryKey: ["job", id],
    queryFn: () => fetchJob(id),
    refetchInterval: (query) =>
      query.state.data?.status === "completed" || query.state.data?.status === "failed" ? false : 2000,
  });

  const { data: files } = useQuery({
    queryKey: ["files", id],
    queryFn: () => fetchFiles(id),
    enabled: job?.status === "completed",
  });

  if (isLoading) return (
    <main style={mainStyle}>
      <div style={{ color: "var(--text-secondary)", fontSize: "15px" }}>Yükleniyor...</div>
    </main>
  );

  if (isError) return (
    <main style={mainStyle}>
      <div style={{ color: "var(--error)" }}>Job bulunamadı.</div>
    </main>
  );

  const isCompleted = job?.status === "completed";
  const isFailed = job?.status === "failed";
  const currentStepIndex = STEPS.findIndex(s => s.key === job?.current_step);

  return (
    <main style={mainStyle}>
      <div style={{ width: "100%", maxWidth: "680px" }}>

        {/* Geri butonu */}
        <Link href="/" style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          color: "var(--text-secondary)",
          fontSize: "13px",
          textDecoration: "none",
          marginBottom: "2rem",
          transition: "color 0.15s",
        }}>← Geri dön</Link>

        {/* Başlık */}
        <div style={{ marginBottom: "2rem" }}>
          <h1 style={{
            fontFamily: "var(--font-display)",
            fontSize: "28px",
            fontWeight: "700",
            letterSpacing: "-0.5px",
            marginBottom: "6px",
          }}>{job?.topic}</h1>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <StatusBadge status={job?.status} />
            <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>ID: {id?.slice(0, 8)}...</span>
          </div>
        </div>

        {/* Pipeline progress */}
        {!isCompleted && !isFailed && (
          <div style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: "16px",
            padding: "1.5rem",
            marginBottom: "1.5rem",
          }}>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "1rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>Pipeline</p>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {STEPS.map((step, i) => {
                const isDone = currentStepIndex > i || isCompleted;
                const isActive = job?.current_step === step.key;
                return (
                  <div key={step.key} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <div style={{
                      width: "24px",
                      height: "24px",
                      borderRadius: "50%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "11px",
                      fontWeight: "600",
                      background: isDone ? "var(--success)" : isActive ? "var(--accent)" : "var(--bg-secondary)",
                      color: isDone || isActive ? "#000" : "var(--text-muted)",
                      border: isActive ? "none" : "1px solid var(--border)",
                      flexShrink: 0,
                      animation: isActive ? "pulse 1.5s infinite" : "none",
                    }}>
                      {isDone ? "✓" : i + 1}
                    </div>
                    <span style={{
                      fontSize: "14px",
                      color: isActive ? "var(--text-primary)" : isDone ? "var(--text-secondary)" : "var(--text-muted)",
                      fontWeight: isActive ? "500" : "400",
                    }}>{step.label}</span>
                    {isActive && <span style={{ fontSize: "11px", color: "var(--accent)", marginLeft: "auto" }}>devam ediyor...</span>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Hata */}
        {isFailed && (
          <div style={{
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: "12px",
            padding: "1rem 1.25rem",
            marginBottom: "1.5rem",
            color: "var(--error)",
            fontSize: "14px",
          }}>
            Hata: {job?.error_msg}
          </div>
        )}

        {/* Video player */}
        {files?.video && (
          <div style={{ marginBottom: "1.5rem" }}>
            <SectionLabel>Video</SectionLabel>
            <div style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "16px",
              overflow: "hidden",
            }}>
              <video controls style={{ width: "100%", display: "block" }}>
                <source src={`${API_URL}${files.video}`} type="video/mp4" />
              </video>
              <div style={{ padding: "1rem", borderTop: "1px solid var(--border)" }}>
                <a
                  href={`${API_URL}${files.video}`}
                  download="video.mp4"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "8px 16px",
                    borderRadius: "8px",
                    background: "var(--accent)",
                    color: "#000",
                    fontSize: "13px",
                    fontWeight: "600",
                    textDecoration: "none",
                  }}
                >↓ İndir</a>
              </div>
            </div>
          </div>
        )}

        {/* Ses player */}
        {files?.audio && (
          <div style={{ marginBottom: "1.5rem" }}>
            <SectionLabel>Ses</SectionLabel>
            <div style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "16px",
              padding: "1rem 1.25rem",
            }}>
              <audio controls style={{ width: "100%" }}>
                <source src={`${API_URL}${files.audio}`} type="audio/mpeg" />
              </audio>
            </div>
          </div>
        )}

        {/* Görseller */}
        {files?.images && files.images.length > 0 && (
          <div style={{ marginBottom: "1.5rem" }}>
            <SectionLabel>Görseller</SectionLabel>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "8px" }}>
              {files.images.map((imgUrl: string, i: number) => (
                <a key={i} href={`${API_URL}${imgUrl}`} target="_blank" rel="noopener noreferrer">
                  <img
                    src={`${API_URL}${imgUrl}`}
                    alt={`Görsel ${i + 1}`}
                    style={{
                      width: "100%",
                      aspectRatio: "16/9",
                      objectFit: "cover",
                      borderRadius: "10px",
                      border: "1px solid var(--border)",
                      transition: "opacity 0.15s",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.8")}
                    onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
                  />
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Senaryo */}
        {job?.result_text && (
          <div style={{ marginBottom: "1.5rem" }}>
            <SectionLabel>Senaryo</SectionLabel>
            <div style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "16px",
              padding: "1.5rem",
              color: "var(--text-secondary)",
              fontSize: "14px",
              lineHeight: "1.8",
              whiteSpace: "pre-wrap",
            }}>
              {job.result_text}
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.7; transform: scale(0.95); }
        }
      `}</style>
    </main>
  );
}

const mainStyle: React.CSSProperties = {
  minHeight: "100vh",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  padding: "3rem 1.5rem",
  background: "var(--bg-primary)",
};

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p style={{
      fontSize: "11px",
      fontWeight: "500",
      color: "var(--text-secondary)",
      letterSpacing: "0.1em",
      textTransform: "uppercase",
      marginBottom: "10px",
    }}>{children}</p>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; color: string; label: string }> = {
    pending: { bg: "rgba(136,136,160,0.15)", color: "#8888a0", label: "Bekliyor" },
    running: { bg: "rgba(245,158,11,0.15)", color: "#f59e0b", label: "İşleniyor" },
    completed: { bg: "rgba(16,185,129,0.15)", color: "#10b981", label: "Tamamlandı" },
    failed: { bg: "rgba(239,68,68,0.15)", color: "#ef4444", label: "Hata" },
  };
  const c = config[status] || config.pending;
  return (
    <span style={{
      padding: "4px 10px",
      borderRadius: "100px",
      background: c.bg,
      color: c.color,
      fontSize: "12px",
      fontWeight: "500",
    }}>{c.label}</span>
  );
}
