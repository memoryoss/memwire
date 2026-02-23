import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type KBDocument } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import {
  BookOpen,
  Plus,
  Trash2,
  Search,
  Link,
  FileText,
  Upload,
  Layers,
} from "lucide-react";

type UploadTab = "text" | "url" | "file";

export default function Knowledge() {
  const agentId = "default";
  const [tab, setTab] = useState<UploadTab>("text");

  // text upload state
  const [docName, setDocName] = useState("");
  const [content, setContent] = useState("");

  // url upload state
  const [url, setUrl] = useState("");
  const [urlDocName, setUrlDocName] = useState("");

  // file upload state
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const [searchQ, setSearchQ] = useState("");
  const qc = useQueryClient();

  const docsKey = ["knowledge", agentId];
  const { data: docs = [], isLoading } = useQuery<KBDocument[]>({
    queryKey: docsKey,
    queryFn: () => api.knowledge.list(agentId),
  });

  const uploadTextMut = useMutation({
    mutationFn: () => api.knowledge.uploadText(agentId, docName, content),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: docsKey });
      setDocName("");
      setContent("");
    },
  });

  const uploadUrlMut = useMutation({
    mutationFn: () =>
      api.knowledge.uploadUrl(agentId, url, urlDocName || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: docsKey });
      setUrl("");
      setUrlDocName("");
    },
  });

  const uploadFileMut = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("No file selected");
      return api.knowledge.uploadFile(agentId, file);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: docsKey });
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
    },
  });

  const deleteMut = useMutation({
    mutationFn: (docId: string) => api.knowledge.delete(agentId, docId),
    onSuccess: () => qc.invalidateQueries({ queryKey: docsKey }),
  });

  const filtered = docs.filter(
    (d) =>
      !searchQ ||
      d.doc_name.toLowerCase().includes(searchQ.toLowerCase())
  );

  const isUploading =
    uploadTextMut.isPending ||
    uploadUrlMut.isPending ||
    uploadFileMut.isPending;

  function handleUpload() {
    if (tab === "text") uploadTextMut.mutate();
    else if (tab === "url") uploadUrlMut.mutate();
    else uploadFileMut.mutate();
  }

  function canUpload() {
    if (!agentId) return false;
    if (tab === "text") return !!docName.trim() && !!content.trim();
    if (tab === "url") return !!url.trim();
    return !!file;
  }

  const sourceIcon = (type: KBDocument["source_type"]) => {
    if (type === "url") return <Link className="h-4 w-4 text-muted-foreground shrink-0" />;
    if (type === "file") return <Upload className="h-4 w-4 text-muted-foreground shrink-0" />;
    return <FileText className="h-4 w-4 text-muted-foreground shrink-0" />;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Knowledge</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Manage knowledge base documents for memory-augmented responses
        </p>
      </div>

      {/* Agent selector removed — memory is now automatic */}

      <>
          {/* ── Upload form ──────────────────────────────────────────── */}
          <div className="rounded-lg border p-4 space-y-3 bg-card">
            <p className="text-sm font-medium">Add Document</p>

            {/* Tabs */}
            <div className="flex gap-2">
              {(["text", "url", "file"] as UploadTab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-3 py-1 text-xs rounded-md capitalize transition-colors ${
                    tab === t
                      ? "bg-primary text-primary-foreground"
                      : "border hover:bg-accent"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* Text tab */}
            {tab === "text" && (
              <>
                <input
                  className="w-full rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none"
                  placeholder="Document name"
                  value={docName}
                  onChange={(e) => setDocName(e.target.value)}
                />
                <textarea
                  rows={4}
                  className="w-full rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none resize-none"
                  placeholder="Paste document content…"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              </>
            )}

            {/* URL tab */}
            {tab === "url" && (
              <>
                <input
                  className="w-full rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none"
                  placeholder="https://example.com/docs"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                />
                <input
                  className="w-full rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none"
                  placeholder="Document name (optional — defaults to URL)"
                  value={urlDocName}
                  onChange={(e) => setUrlDocName(e.target.value)}
                />
              </>
            )}

            {/* File tab */}
            {tab === "file" && (
              <div
                className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:border-primary/50 transition-colors"
                onClick={() => fileRef.current?.click()}
              >
                <Upload className="h-6 w-6 mx-auto mb-2 text-muted-foreground" />
                {file ? (
                  <p className="text-sm font-medium">{file.name}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Click to choose a file (.pdf, .txt, .md, .json, .csv)
                  </p>
                )}
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.txt,.md,.json,.csv"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </div>
            )}

            {/* Upload errors */}
            {(uploadTextMut.error ||
              uploadUrlMut.error ||
              uploadFileMut.error) && (
              <p className="text-xs text-destructive">
                {(
                  (uploadTextMut.error ||
                    uploadUrlMut.error ||
                    uploadFileMut.error) as Error
                ).message}
              </p>
            )}

            <div className="flex justify-end">
              <button
                disabled={!canUpload() || isUploading}
                onClick={handleUpload}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground disabled:opacity-50"
              >
                <Plus className="h-3.5 w-3.5" />
                {isUploading ? "Uploading…" : "Upload"}
              </button>
            </div>
          </div>

          {/* ── Search bar ───────────────────────────────────────────── */}
          <div className="flex items-center gap-2 border rounded-md px-3 py-1.5">
            <Search className="h-4 w-4 text-muted-foreground" />
            <input
              className="text-sm bg-transparent focus:outline-none flex-1"
              placeholder="Search documents…"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
            />
          </div>

          {/* ── Document list ────────────────────────────────────────── */}
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : filtered.length === 0 ? (
            <div className="rounded-lg border border-dashed px-6 py-10 text-center">
              <BookOpen className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">
                No documents yet. Upload one above.
              </p>
            </div>
          ) : (
            <div className="rounded-lg border divide-y">
              {filtered.map((doc) => (
                <div
                  key={doc.doc_id}
                  className="flex items-center gap-3 px-4 py-3"
                >
                  {sourceIcon(doc.source_type)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {doc.doc_name}
                    </p>
                    <p className="text-xs text-muted-foreground flex items-center gap-2">
                      <span className="capitalize">{doc.source_type}</span>
                      {doc.chunk_count > 0 && (
                        <>
                          <span>·</span>
                          <Layers className="h-3 w-3 inline" />
                          <span>{doc.chunk_count} chunks</span>
                        </>
                      )}
                      <span>·</span>
                      <span>{formatDate(doc.created_at)}</span>
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      if (confirm(`Delete "${doc.doc_name}"?`))
                        deleteMut.mutate(doc.doc_id);
                    }}
                    className="p-1.5 rounded hover:bg-destructive/10"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-destructive" />
                  </button>
                </div>
              ))}
            </div>
          )}
      </>
    </div>
  );
}

