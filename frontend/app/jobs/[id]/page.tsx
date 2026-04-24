"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const STEPS = ["text", "audio", "images", "video"];
const STEP_LABELS: Record<string, string> = {
  text: "Metin üretiliyor",
  audio: "Ses oluşturuluyor",
  images: "Görseller üretiliyor",
  video: "Video hazırlanıyor",
};

const BASE_URL = "http://localhost:8000";

async function fetchJob(id: string) {
  const res = await fetch(`${BASE_URL}/api/jobs/${id}`);
  if (!res.ok) throw new Error("Job bulunamadı");
  return res.json();
}

async function fetchFiles(id: string) {
  const res = await fetch(`${BASE_URL}/api/jobs/${id}/files`);
  if (!res.ok) return null;
  return res.json();
}

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: job, isLoading, isError } = useQuery({
    queryKey: ["job", id],
    queryFn: () => fetchJob(id),
    refetchInterval: (query) =>
      query.state.data?.status === "completed" ||
      query.state.data?.status === "failed"
        ? false
        : 2000,
  });

  const { data: files } = useQuery({
    queryKey: ["files", id],
    queryFn: () => fetchFiles(id),
    enabled: job?.status === "completed",
  });

  if (isLoading) return <p className="p-8">Yükleniyor...</p>;
  if (isError) return <p className="p-8 text-red-500">Job bulunamadı.</p>;

  const currentStepIndex = STEPS.indexOf(job.current_step ?? "");
  const isCompleted = job.status === "completed";
  const isFailed = job.status === "failed";

  return (
    <main className="min-h-screen bg-background p-8 max-w-2xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>📋 {job.topic}</CardTitle>
          <p className="text-sm text-muted-foreground">ID: {job.id}</p>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">

          {/* Progress Steps */}
          <div className="flex flex-col gap-2">
            {STEPS.map((step, i) => {
              const isDone = isCompleted || i < currentStepIndex;
              const isActive = job.current_step === step;
              return (
                <div key={step} className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
                    ${isDone ? "bg-green-500 text-white" : isActive ? "bg-blue-500 text-white animate-pulse" : "bg-muted text-muted-foreground"}`}>
                    {isDone ? "✓" : i + 1}
                  </div>
                  <span className={`text-sm ${isActive ? "font-semibold" : ""}`}>
                    {STEP_LABELS[step]}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Status Badge */}
          <div>
            {isCompleted && <span className="text-green-600 font-semibold">✅ Tamamlandı</span>}
            {isFailed && <span className="text-red-500 font-semibold">❌ Hata: {job.error_msg}</span>}
            {!isCompleted && !isFailed && <span className="text-blue-500 font-semibold animate-pulse">⏳ İşleniyor...</span>}
          </div>

          {/* Ses Player */}
          {files?.audio && (
            <div className="flex flex-col gap-2">
              <h3 className="font-semibold">🎵 Ses Önizleme</h3>
              <audio controls className="w-full">
                <source src={`${BASE_URL}${files.audio}`} type="audio/mpeg" />
              </audio>
            </div>
          )}

          {/* Görseller Grid */}
          {files?.images && files.images.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="font-semibold">🖼️ Görseller</h3>
              <div className="grid grid-cols-3 gap-2">
                {files.images.map((imgUrl: string, i: number) => (
                  <a key={i} href={`${BASE_URL}${imgUrl}`} target="_blank" rel="noopener noreferrer">
                    <img
                      src={`${BASE_URL}${imgUrl}`}
                      alt={`Görsel ${i + 1}`}
                      className="w-full rounded-md border hover:opacity-80 transition-opacity cursor-pointer"
                    />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Senaryo */}
          {job.result_text && (
            <div className="flex flex-col gap-2">
              <h3 className="font-semibold">📝 Üretilen Senaryo</h3>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap bg-muted p-4 rounded-md">
                {job.result_text}
              </p>
            </div>
          )}

        </CardContent>
      </Card>
    </main>
  );
}