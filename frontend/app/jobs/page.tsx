"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

async function fetchJobs() {
  const res = await fetch("http://localhost:8000/api/jobs");
  if (!res.ok) throw new Error("Joblar alınamadı");
  return res.json();
}

const STATUS_STYLES: Record<string, string> = {
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  running: "bg-blue-100 text-blue-700",
  pending: "bg-gray-100 text-gray-600",
};

const STATUS_LABELS: Record<string, string> = {
  completed: "✅ Tamamlandı",
  failed: "❌ Hata",
  running: "⏳ Çalışıyor",
  pending: "🕐 Bekliyor",
};

export default function JobsPage() {
  const router = useRouter();

  const { data: jobs, isLoading, isError } = useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
    refetchInterval: 5000,
  });

  if (isLoading) return <p className="p-8">Yükleniyor...</p>;
  if (isError) return <p className="p-8 text-red-500">Joblar alınamadı.</p>;

  return (
    <main className="min-h-screen bg-background p-8 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">📋 Geçmiş İşler</h1>
        <button
          onClick={() => router.push("/")}
          className="text-sm text-muted-foreground hover:underline"
        >
          + Yeni Video
        </button>
      </div>

      <div className="flex flex-col gap-3">
        {jobs.map((job: any) => (
          <Card
            key={job.id}
            className="cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => router.push(`/jobs/${job.id}`)}
          >
            <CardContent className="flex items-center justify-between py-4">
              <div>
                <p className="font-semibold capitalize">{job.topic}</p>
                <p className="text-xs text-muted-foreground font-mono">{job.id}</p>
              </div>
              <span
                className={`text-xs px-2 py-1 rounded-full font-medium ${STATUS_STYLES[job.status] ?? "bg-gray-100"}`}
              >
                {STATUS_LABELS[job.status] ?? job.status}
              </span>
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  );
}