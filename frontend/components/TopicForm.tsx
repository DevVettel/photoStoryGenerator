"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function TopicForm() {
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const [language, setLanguage] = useState<string>("tr");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!topic.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch("http://localhost:8000/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, language }),
      });

      if (!res.ok) throw new Error("Sunucu hatası");

      const data = await res.json();
      router.push(`/jobs/${data.id}`);
    } catch (err) {
      setError("Backend'e bağlanılamadı. Sunucunun çalıştığından emin ol.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-lg mx-auto mt-20">
      <CardHeader>
        <CardTitle>📹 PhotoStory — Video Üret</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="topic">Konu</Label>
          <Input
            id="topic"
            placeholder="örn. Mars kolonisi, Osmanlı tarihi..."
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="language">Dil</Label>
          <Select value={language} onValueChange={(value) => value && setLanguage(value)}>
            <SelectTrigger id="language">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="tr">Türkçe</SelectItem>
              <SelectItem value="en">English</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button onClick={handleSubmit} disabled={loading || !topic.trim()}>
          {loading ? "Gönderiliyor..." : "Video Üret"}
        </Button>

        {error && (
          <p className="text-sm text-red-500">⚠️ {error}</p>
        )}
      </CardContent>
    </Card>
  );
}