import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  api,
  type AppSettings,
  type SettingsUpdate,
  type LLMConfig,
  type EmbedderConfig,
  type DatabaseConfig,
} from "@/lib/api";
import {
  Check,
  ChevronRight,
  Database,
  Settings as SettingsIcon,
  X,
  Eye,
  EyeOff,
  RefreshCw,
  Cpu,
  Layers,
  ServerCrash,
} from "lucide-react";

// ── Provider definitions ───────────────────────────────────────────────────

const LLM_PROVIDERS = [
  {
    id: "openai",
    name: "OpenAI",
    description: "GPT-4o, GPT-4o mini, GPT-3.5 Turbo",
    color: "bg-emerald-500",
    letter: "OAI",
    models: ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4-turbo"],
  },
  {
    id: "azure_openai",
    name: "Azure OpenAI",
    description: "Self-hosted via Azure endpoint",
    color: "bg-blue-500",
    letter: "AZ",
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-35-turbo"],
  },
  {
    id: "anthropic",
    name: "Anthropic",
    description: "Claude 3.5 Sonnet, Claude 3 Haiku",
    color: "bg-orange-500",
    letter: "AN",
    models: ["claude-3-5-sonnet-latest", "claude-3-haiku-20240307", "claude-3-opus-20240229"],
  },
  {
    id: "ollama",
    name: "Ollama",
    description: "Local models via Ollama",
    color: "bg-purple-500",
    letter: "OL",
    models: [],
  },
  {
    id: "custom",
    name: "Custom",
    description: "Any OpenAI-compatible endpoint",
    color: "bg-slate-500",
    letter: "CS",
    models: [],
  },
];

const EMBEDDER_PROVIDERS = [
  {
    id: "openai",
    name: "OpenAI",
    description: "text-embedding-3-small/large",
    color: "bg-emerald-500",
    letter: "OAI",
    models: ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
  },
  {
    id: "azure_openai",
    name: "Azure OpenAI",
    description: "Azure-hosted embedding model",
    color: "bg-blue-500",
    letter: "AZ",
    models: ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
  },
  {
    id: "ollama",
    name: "Ollama",
    description: "Local embedding via Ollama",
    color: "bg-purple-500",
    letter: "OL",
    models: ["nomic-embed-text", "mxbai-embed-large"],
  },
];

// ── Helper components ──────────────────────────────────────────────────────

function ProviderAvatar({ color, letter }: { color: string; letter: string }) {
  return (
    <div
      className={`h-11 w-11 rounded-xl ${color} flex items-center justify-center shrink-0`}
    >
      <span className="text-white text-xs font-bold tracking-wide">{letter}</span>
    </div>
  );
}

function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-foreground/80">{label}</label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function TextInput({
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full rounded-md border px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
    />
  );
}

function SecretInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <input
        type={visible ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 pr-9"
      />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
      >
        {visible ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
      </button>
    </div>
  );
}

function SelectInput({
  value,
  onChange,
  options,
  allowCustom,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  allowCustom?: boolean;
}) {
  const isCustom = allowCustom && options.length > 0 && !options.includes(value) && value !== "";
  return (
    <div className="space-y-1.5">
      {options.length > 0 && (
        <select
          className="w-full rounded-md border px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
          value={isCustom ? "__custom__" : value}
          onChange={(e) => {
            if (e.target.value !== "__custom__") onChange(e.target.value);
          }}
        >
          {options.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
          {allowCustom && <option value="__custom__">Custom…</option>}
        </select>
      )}
      {(options.length === 0 || isCustom) && (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="model name"
          className="w-full rounded-md border px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
      )}
    </div>
  );
}

// ── Modal ──────────────────────────────────────────────────────────────────

type ModalType = "llm" | "embedder" | "database";

function Modal({
  title,
  onClose,
  onSave,
  saving,
  error,
  children,
}: {
  title: string;
  onClose: () => void;
  onSave: () => void;
  saving: boolean;
  error?: string | null;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-card border rounded-xl shadow-xl w-full max-w-md mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b shrink-0">
          <h2 className="font-semibold text-sm">{title}</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-accent">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">{children}</div>

        {/* Error */}
        {error && (
          <div className="mx-5 mb-2 rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-xs text-destructive">
            {error}
          </div>
        )}

        {/* Footer */}
        <div className="flex gap-2 justify-end px-5 py-4 border-t shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-md border hover:bg-accent"
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 text-sm rounded-md bg-primary text-primary-foreground disabled:opacity-50"
          >
            {saving ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Check className="h-3.5 w-3.5" />
            )}
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── LLM Configure Modal ────────────────────────────────────────────────────

function LLMModal({
  provider,
  current,
  onClose,
  onSave,
  saving,
  error,
}: {
  provider: (typeof LLM_PROVIDERS)[number];
  current: LLMConfig;
  onClose: () => void;
  onSave: (cfg: SettingsUpdate["llm"]) => void;
  saving: boolean;
  error?: string | null;
}) {
  const [model, setModel] = useState(
    current.provider === provider.id ? current.model : (provider.models[0] ?? "")
  );
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(current.base_url ?? "");
  const [apiVersion, setApiVersion] = useState(current.azure_api_version ?? "2024-02-15-preview");

  return (
    <Modal
      title={`Configure ${provider.name}`}
      onClose={onClose}
      onSave={() =>
        onSave({
          provider: provider.id,
          model,
          api_key: apiKey || undefined,
          base_url: baseUrl || undefined,
          azure_api_version: provider.id === "azure_openai" ? apiVersion : undefined,
        })
      }
      saving={saving}
      error={error}
    >
      {/* API Key — all except Ollama */}
      {provider.id !== "ollama" && (
        <Field
          label="API Key"
          hint={
            current.provider === provider.id && current.api_key_set
              ? "Leave blank to keep existing key"
              : undefined
          }
        >
          <SecretInput
            value={apiKey}
            onChange={setApiKey}
            placeholder={
              current.provider === provider.id && current.api_key_set
                ? "••••••••••••••••"
                : "sk-..."
            }
          />
        </Field>
      )}

      {/* Base URL — Azure, Ollama, Custom */}
      {(provider.id === "azure_openai" ||
        provider.id === "ollama" ||
        provider.id === "custom") && (
        <Field
          label={provider.id === "azure_openai" ? "Azure Endpoint" : "Base URL"}
          hint={
            provider.id === "azure_openai"
              ? "https://your-resource.openai.azure.com/"
              : provider.id === "ollama"
              ? "http://localhost:11434"
              : undefined
          }
        >
          <TextInput
            value={baseUrl}
            onChange={setBaseUrl}
            placeholder={
              provider.id === "azure_openai"
                ? "https://your-resource.openai.azure.com/"
                : "http://localhost:11434"
            }
          />
        </Field>
      )}

      {/* Azure API Version */}
      {provider.id === "azure_openai" && (
        <Field label="API Version">
          <SelectInput
            value={apiVersion}
            onChange={setApiVersion}
            options={["2024-02-15-preview", "2024-05-01-preview", "2023-12-01-preview"]}
          />
        </Field>
      )}

      {/* Model */}
      <Field label="Model">
        <SelectInput
          value={model}
          onChange={setModel}
          options={provider.models}
          allowCustom
        />
      </Field>
    </Modal>
  );
}

// ── Embedder Configure Modal ───────────────────────────────────────────────

function EmbedderModal({
  provider,
  current,
  onClose,
  onSave,
  saving,
  error,
}: {
  provider: (typeof EMBEDDER_PROVIDERS)[number];
  current: EmbedderConfig;
  onClose: () => void;
  onSave: (cfg: SettingsUpdate["embedder"]) => void;
  saving: boolean;
  error?: string | null;
}) {
  const [model, setModel] = useState(
    current.provider === provider.id ? current.model : (provider.models[0] ?? "")
  );
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(current.base_url ?? "");
  const [dimensions, setDimensions] = useState(String(current.dimensions ?? 1536));

  return (
    <Modal
      title={`Configure ${provider.name} Embedder`}
      onClose={onClose}
      onSave={() =>
        onSave({
          provider: provider.id,
          model,
          api_key: apiKey || undefined,
          base_url: baseUrl || undefined,
          dimensions: Number(dimensions) || 1536,
        })
      }
      saving={saving}
      error={error}
    >
      {provider.id !== "ollama" && (
        <Field
          label="API Key"
          hint={
            current.provider === provider.id && current.api_key_set
              ? "Leave blank to keep existing key"
              : undefined
          }
        >
          <SecretInput
            value={apiKey}
            onChange={setApiKey}
            placeholder={
              current.provider === provider.id && current.api_key_set
                ? "••••••••••••••••"
                : "sk-..."
            }
          />
        </Field>
      )}

      {(provider.id === "azure_openai" || provider.id === "ollama") && (
        <Field
          label={provider.id === "azure_openai" ? "Azure Endpoint" : "Base URL"}
        >
          <TextInput
            value={baseUrl}
            onChange={setBaseUrl}
            placeholder={
              provider.id === "azure_openai"
                ? "https://your-resource.openai.azure.com/"
                : "http://localhost:11434"
            }
          />
        </Field>
      )}

      <Field label="Model">
        <SelectInput
          value={model}
          onChange={setModel}
          options={provider.models}
          allowCustom
        />
      </Field>

      <Field label="Dimensions" hint="Must match the chosen model's output dimensions">
        <TextInput value={dimensions} onChange={setDimensions} placeholder="1536" />
      </Field>
    </Modal>
  );
}

// ── Database Configure Modal ───────────────────────────────────────────────

function DatabaseModal({
  current,
  onClose,
  onSave,
  saving,
  error,
}: {
  current: DatabaseConfig;
  onClose: () => void;
  onSave: (cfg: SettingsUpdate["database"]) => void;
  saving: boolean;
  error?: string | null;
}) {
  const [useBundled, setUseBundled] = useState(current.use_bundled);
  const [host, setHost] = useState(current.host ?? "");
  const [port, setPort] = useState(String(current.port ?? 5432));
  const [dbName, setDbName] = useState(current.database ?? "");
  const [username, setUsername] = useState(current.username ?? "");
  const [password, setPassword] = useState("");

  return (
    <Modal
      title="Configure PostgreSQL"
      onClose={onClose}
      onSave={() =>
        onSave({
          use_bundled: useBundled,
          host: useBundled ? undefined : host || undefined,
          port: useBundled ? undefined : Number(port) || 5432,
          database: useBundled ? undefined : dbName || undefined,
          username: useBundled ? undefined : username || undefined,
          password: useBundled ? undefined : password || undefined,
        })
      }
      saving={saving}
      error={error}
    >
      {/* Toggle */}
      <div className="flex items-center justify-between rounded-lg border px-4 py-3">
        <div>
          <p className="text-sm font-medium">Use bundled database</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Runs a PostgreSQL container managed by MemWire
          </p>
        </div>
        <button
          type="button"
          onClick={() => setUseBundled((v) => !v)}
          className={`relative w-10 h-5 rounded-full transition-colors ${
            useBundled ? "bg-primary" : "bg-muted"
          }`}
        >
          <span
            className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
              useBundled ? "translate-x-5" : "translate-x-0.5"
            }`}
          />
        </button>
      </div>

      {/* External DB fields */}
      {!useBundled && (
        <>
          <Field label="Host">
            <TextInput value={host} onChange={setHost} placeholder="db.example.com" />
          </Field>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-1">
              <Field label="Port">
                <TextInput value={port} onChange={setPort} placeholder="5432" />
              </Field>
            </div>
            <div className="col-span-2">
              <Field label="Database">
                <TextInput value={dbName} onChange={setDbName} placeholder="memwire" />
              </Field>
            </div>
          </div>
          <Field label="Username">
            <TextInput value={username} onChange={setUsername} placeholder="memwire" />
          </Field>
          <Field label="Password">
            <SecretInput value={password} onChange={setPassword} placeholder="••••••" />
          </Field>
        </>
      )}
    </Modal>
  );
}

// ── Provider Card ──────────────────────────────────────────────────────────

function ProviderCard({
  letter,
  color,
  name,
  description,
  isActive,
  model,
  onConfigure,
}: {
  letter: string;
  color: string;
  name: string;
  description: string;
  isActive: boolean;
  model?: string;
  onConfigure: () => void;
}) {
  return (
    <div
      className={`relative rounded-xl border p-4 flex flex-col gap-3 transition-all ${
        isActive
          ? "border-primary bg-primary/5 ring-1 ring-primary/20"
          : "hover:border-primary/30 hover:bg-accent/40"
      }`}
    >
      {/* Active badge */}
      {isActive && (
        <span className="absolute top-3 right-3 flex items-center gap-1 text-[10px] font-semibold text-primary bg-primary/10 rounded-full px-2 py-0.5">
          <Check className="h-3 w-3" /> Active
        </span>
      )}

      <div className="flex items-start gap-3">
        <ProviderAvatar color={color} letter={letter} />
        <div className="min-w-0 flex-1 pt-0.5">
          <p className="text-sm font-semibold leading-tight">{name}</p>
          <p className="text-xs text-muted-foreground mt-0.5 leading-snug">{description}</p>
          {isActive && model && (
            <p className="text-xs font-mono text-primary/80 mt-1 truncate">{model}</p>
          )}
        </div>
      </div>

      <button
        onClick={onConfigure}
        className="mt-auto flex items-center justify-center gap-1.5 w-full rounded-lg border border-primary/30 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/5 transition-colors"
      >
        Configure <ChevronRight className="h-3 w-3" />
      </button>
    </div>
  );
}

// ── API Key Section (kept from original) ──────────────────────────────────

function ApiKeyInput() {
  const current = localStorage.getItem("mw_api_key") ?? "";
  const [val, setVal] = useState(current);
  const [saved, setSaved] = useState(false);

  const save = () => {
    localStorage.setItem("mw_api_key", val);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="flex gap-2">
      <input
        type="password"
        value={val}
        onChange={(e) => setVal(e.target.value)}
        placeholder="mw_..."
        className="flex-1 rounded-md border px-3 py-1.5 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono"
      />
      <button
        onClick={save}
        className={`px-3 py-1.5 text-sm rounded-md transition-all ${
          saved
            ? "bg-green-600 text-white"
            : "bg-primary text-primary-foreground hover:bg-primary/90"
        }`}
      >
        {saved ? <Check className="h-4 w-4" /> : "Save"}
      </button>
    </div>
  );
}

// ── Main Settings Page ─────────────────────────────────────────────────────

type Tab = "llm" | "embedder" | "database";

type ModalState =
  | { type: "llm"; provider: (typeof LLM_PROVIDERS)[number] }
  | { type: "embedder"; provider: (typeof EMBEDDER_PROVIDERS)[number] }
  | { type: "database" }
  | null;

export default function Settings() {
  const [tab, setTab] = useState<Tab>("llm");
  const [modal, setModal] = useState<ModalState>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const qc = useQueryClient();

  const { data: settings, isLoading, error: loadError } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.settings.get(),
    retry: false,
  });

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health.get(),
    retry: false,
  });

  const saveMut = useMutation({
    mutationFn: (body: SettingsUpdate) => api.settings.update(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      setSaveError(null);
      setModal(null);
    },
    onError: (e: Error) => {
      setSaveError(e.message);
    },
  });

  const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "llm", label: "Language Model", icon: <Cpu className="h-4 w-4" /> },
    { id: "embedder", label: "Embedder", icon: <Layers className="h-4 w-4" /> },
    { id: "database", label: "Database", icon: <Database className="h-4 w-4" /> },
  ];

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Settings</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Configure your LLM provider, embedder, and database
          </p>
        </div>

        {/* API status */}
        <div className="flex items-center gap-2 text-sm rounded-lg border px-3 py-1.5">
          <span
            className={`h-2 w-2 rounded-full ${health ? "bg-green-500" : "bg-red-400"}`}
          />
          <span className="text-xs text-muted-foreground">
            {health ? `API v${health.version}` : "API unreachable"}
          </span>
        </div>
      </div>

      {/* Dashboard API Key */}
      <div className="rounded-xl border p-4 space-y-2">
        <div>
          <p className="text-sm font-medium">Dashboard API Key</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Used by this dashboard to authenticate with the MemWire API.
            Stored in <code className="text-xs bg-muted px-1 rounded">localStorage</code>.
          </p>
        </div>
        <ApiKeyInput />
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Loading / Error */}
      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
          <RefreshCw className="h-4 w-4 animate-spin" />
          Loading configuration…
        </div>
      )}
      {loadError && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 flex items-center gap-2">
          <ServerCrash className="h-4 w-4 text-destructive shrink-0" />
          <p className="text-sm text-destructive">
            Could not load settings. Make sure the API is reachable.
          </p>
        </div>
      )}

      {settings && (
        <>
          {/* ── LLM Tab ─────────────────────────────────────────────── */}
          {tab === "llm" && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Choose the language model that powers conversation and reasoning.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {LLM_PROVIDERS.map((p) => (
                  <ProviderCard
                    key={p.id}
                    letter={p.letter}
                    color={p.color}
                    name={p.name}
                    description={p.description}
                    isActive={settings.llm.provider === p.id}
                    model={settings.llm.provider === p.id ? settings.llm.model : undefined}
                    onConfigure={() => {
                      setSaveError(null);
                      setModal({ type: "llm", provider: p });
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* ── Embedder Tab ─────────────────────────────────────────── */}
          {tab === "embedder" && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Choose the embedding model used for knowledge base vector search.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {EMBEDDER_PROVIDERS.map((p) => (
                  <ProviderCard
                    key={p.id}
                    letter={p.letter}
                    color={p.color}
                    name={p.name}
                    description={p.description}
                    isActive={settings.embedder.provider === p.id}
                    model={
                      settings.embedder.provider === p.id
                        ? settings.embedder.model
                        : undefined
                    }
                    onConfigure={() => {
                      setSaveError(null);
                      setModal({ type: "embedder", provider: p });
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* ── Database Tab ─────────────────────────────────────────── */}
          {tab === "database" && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Configure the PostgreSQL database used for memory and knowledge storage.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* PostgreSQL card */}
                <div
                  className="rounded-xl border border-primary bg-primary/5 ring-1 ring-primary/20 p-4 flex flex-col gap-3"
                >
                  <span className="self-start flex items-center gap-1 text-[10px] font-semibold text-primary bg-primary/10 rounded-full px-2 py-0.5">
                    <Check className="h-3 w-3" /> Active
                  </span>
                  <div className="flex items-start gap-3">
                    <div className="h-11 w-11 rounded-xl bg-blue-600 flex items-center justify-center shrink-0">
                      <span className="text-white text-xs font-bold">PG</span>
                    </div>
                    <div className="pt-0.5">
                      <p className="text-sm font-semibold">PostgreSQL</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {settings.database.use_bundled
                          ? "Bundled container (managed)"
                          : `${settings.database.host ?? "external"}:${settings.database.port}`}
                      </p>
                      {!settings.database.use_bundled && settings.database.database && (
                        <p className="text-xs font-mono text-primary/80 mt-1">
                          {settings.database.username}@{settings.database.database}
                        </p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setSaveError(null);
                      setModal({ type: "database" });
                    }}
                    className="mt-auto flex items-center justify-center gap-1.5 w-full rounded-lg border border-primary/30 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/5 transition-colors"
                  >
                    Configure <ChevronRight className="h-3 w-3" />
                  </button>
                </div>

                {/* Future providers placeholder */}
                <div className="rounded-xl border border-dashed p-4 flex flex-col items-center justify-center gap-2 opacity-40 select-none">
                  <Database className="h-6 w-6 text-muted-foreground" />
                  <p className="text-xs text-muted-foreground">More coming soon</p>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Modals ──────────────────────────────────────────────────────── */}

      {modal?.type === "llm" && settings && (
        <LLMModal
          provider={modal.provider}
          current={settings.llm}
          onClose={() => setModal(null)}
          onSave={(cfg) => saveMut.mutate({ llm: cfg })}
          saving={saveMut.isPending}
          error={saveError}
        />
      )}

      {modal?.type === "embedder" && settings && (
        <EmbedderModal
          provider={modal.provider}
          current={settings.embedder}
          onClose={() => setModal(null)}
          onSave={(cfg) => saveMut.mutate({ embedder: cfg })}
          saving={saveMut.isPending}
          error={saveError}
        />
      )}

      {modal?.type === "database" && settings && (
        <DatabaseModal
          current={settings.database}
          onClose={() => setModal(null)}
          onSave={(cfg) => saveMut.mutate({ database: cfg })}
          saving={saveMut.isPending}
          error={saveError}
        />
      )}
    </div>
  );
}

// keep original API key input exported for auth page reuse
