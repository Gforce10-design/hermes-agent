import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  Bot,
  Boxes,
  CheckCircle2,
  CircleAlert,
  Command,
  ExternalLink,
  Inbox,
  LockKeyhole,
  Loader2,
  MessagesSquare,
  Network,
  Play,
  RefreshCw,
  Rocket,
  Server,
  ShieldCheck,
  Sparkles,
  Wifi,
} from "lucide-react";
import { api } from "@/lib/api";
import type { ConsoleOverview, SessionInfo } from "@/lib/api";
import { timeAgo } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function stateVariant(state: string): "success" | "warning" | "outline" {
  const normalized = state.toLowerCase();
  if (["running", "connected", "active"].includes(normalized)) return "success";
  if (["planned", "idle", "starting"].includes(normalized)) return "warning";
  return "outline";
}

function stateLabel(state: string | null | undefined) {
  const normalized = (state || "unknown").toLowerCase();
  const labels: Record<string, string> = {
    active: "활성",
    connected: "연결됨",
    idle: "대기",
    planned: "예정",
    running: "실행 중",
    starting: "시작 중",
    stopped: "중지됨",
    unknown: "확인 필요",
  };
  return labels[normalized] ?? state ?? "확인 필요";
}

function MetricCard({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: typeof Activity;
  label: string;
  value: number | string;
  detail: string;
}) {
  return (
    <Card className="overflow-hidden border-white/10 bg-white/[0.035] shadow-[0_0_0_1px_rgba(255,255,255,0.03),0_20px_70px_rgba(0,0,0,0.35)]">
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="rounded-xl border border-white/10 bg-white/[0.04] p-2 text-primary">
            <Icon className="h-4 w-4" />
          </div>
          <span className="font-mono text-[10px] text-muted-foreground">실시간</span>
        </div>
        <div className="mt-5 text-xs text-muted-foreground">{label}</div>
        <div className="mt-2 font-expanded text-3xl text-foreground">{value}</div>
        <div className="mt-2 text-xs leading-5 text-muted-foreground normal-case">{detail}</div>
      </CardContent>
    </Card>
  );
}

function QuickAction({
  icon: Icon,
  title,
  detail,
  href,
  tone = "default",
}: {
  icon: typeof Activity;
  title: string;
  detail: string;
  href?: string;
  tone?: "default" | "primary" | "success" | "warning";
}) {
  const toneClass = {
    default: "from-white/[0.05] to-white/[0.025] text-foreground",
    primary: "from-primary/25 to-white/[0.035] text-primary",
    success: "from-success/20 to-white/[0.035] text-success",
    warning: "from-warning/20 to-white/[0.035] text-warning",
  }[tone];
  const content = (
    <div className={`group flex min-h-28 items-center justify-between gap-3 rounded-2xl border border-white/10 bg-gradient-to-br ${toneClass} p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] transition hover:border-white/20 hover:bg-white/[0.06]`}>
      <div className="flex min-w-0 items-start gap-3">
        <div className="rounded-xl border border-white/10 bg-black/25 p-2">
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="font-expanded text-sm text-foreground">{title}</div>
          <div className="mt-2 text-xs leading-5 text-muted-foreground normal-case">{detail}</div>
        </div>
      </div>
      {href ? <ArrowRight className="h-4 w-4 shrink-0 opacity-60 transition group-hover:translate-x-0.5 group-hover:opacity-100" /> : null}
    </div>
  );

  return href ? <Link to={href}>{content}</Link> : content;
}

function SessionRow({ session }: { session: SessionInfo }) {
  return (
    <div className="group flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-white/[0.025] px-3 py-3 transition-colors hover:bg-white/[0.05]">
      <div className="min-w-0">
        <div className="truncate text-sm text-foreground normal-case">
          {session.title || session.preview || "제목 없는 세션"}
        </div>
        <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
          <span>{session.source || "출처 미상"}</span>
          <span>·</span>
          <span>{session.model || "모델 미상"}</span>
        </div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-2 sm:flex-row sm:items-center">
        <Badge variant={session.is_active ? "success" : "outline"}>
          {session.is_active ? "진행 중" : timeAgo(session.last_active)}
        </Badge>
        <Link
          to={`/chat?resume=${encodeURIComponent(session.id)}`}
          className="rounded-full border border-white/10 px-3 py-1 text-[10px] text-muted-foreground transition hover:border-primary/50 hover:text-primary"
        >
          채팅에서 이어가기
        </Link>
      </div>
    </div>
  );
}

export default function ConsolePage() {
  const [overview, setOverview] = useState<ConsoleOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setOverview(await api.getConsoleOverview());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading && !overview) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> 콘솔을 불러오는 중입니다…
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <Card className="max-w-xl border-destructive/30 bg-destructive/10">
          <CardContent className="flex gap-3 p-5 text-destructive normal-case">
            <CircleAlert className="h-5 w-5 shrink-0" /> {error}
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!overview) return null;

  return (
    <div className="h-full overflow-auto bg-[#07080a] p-3 text-foreground lg:p-6">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(113,112,255,0.18),transparent_34%),radial-gradient(circle_at_85%_15%,rgba(255,99,99,0.10),transparent_28%)]" />
      <div className="relative mx-auto flex max-w-7xl flex-col gap-5">
        <section className="overflow-hidden rounded-3xl border border-white/10 bg-[#0f1011]/85 shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_40px_120px_rgba(0,0,0,0.45)]">
          <div className="grid gap-5 p-5 lg:grid-cols-[1.2fr_0.8fr] lg:p-7">
            <div>
              <div className="mb-4 flex flex-wrap items-center gap-2">
                <Badge variant="success">로컬 실행</Badge>
                <Badge variant={stateVariant(overview.status.gateway_state || "unknown")}>게이트웨이 {stateLabel(overview.status.gateway_state)}</Badge>
                <Badge variant="outline">웹 콘솔 v2</Badge>
                <Badge variant="outline"><LockKeyhole className="mr-1 h-3 w-3" /> Access 보호됨</Badge>
              </div>
              <div className="flex items-center gap-3 text-xs text-primary tracking-[0.18em]">
                <Sparkles className="h-4 w-4" /> HERMES COMMAND CENTER
              </div>
              <h1 className="mt-4 max-w-3xl font-expanded text-3xl leading-tight text-foreground lg:text-5xl">
                Hermes 작업 지휘실
              </h1>
              <p className="mt-4 max-w-3xl text-sm leading-6 text-muted-foreground normal-case lg:text-base">
                Telegram 대체 UI로 확장하기 전, 세션·게이트웨이·인프라 제어 대상을 한 화면에서 보는 관제 콘솔입니다.
                지금 단계는 보기와 확인 중심이며 실제 운영 액션은 승인 후 연결합니다.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="mb-3 flex items-center justify-between text-xs text-muted-foreground">
                <span>현재 스냅샷</span>
                <Button onClick={() => void load()} disabled={loading} variant="outline" size="sm">
                  <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} /> 새로고침
                </Button>
              </div>
              <div className="grid gap-2 text-sm normal-case">
                <div className="flex items-center justify-between rounded-xl bg-white/[0.035] px-3 py-2">
                  <span className="text-muted-foreground">Hermes 홈</span>
                  <span className="max-w-48 truncate text-right font-mono text-xs">{overview.status.hermes_home}</span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-white/[0.035] px-3 py-2">
                  <span className="text-muted-foreground">프로세스</span>
                  <span className="font-mono text-xs">PID {overview.status.gateway_pid || "—"}</span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-white/[0.035] px-3 py-2">
                  <span className="text-muted-foreground">디자인 기준</span>
                  <span className="text-right text-xs">Linear · Raycast · Superhuman</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard icon={MessagesSquare} label="활성 세션" value={overview.metrics.active_sessions} detail="최근 5분 안에 움직인 Hermes 작업" />
          <MetricCard icon={Activity} label="최근 세션" value={overview.metrics.recent_sessions} detail="콘솔 스냅샷에 불러온 작업 목록" />
          <MetricCard icon={Wifi} label="연결 채널" value={overview.metrics.connected_platforms} detail="현재 연결된 게이트웨이 플랫폼" />
          <MetricCard icon={Command} label="제어 대상" value={overview.metrics.control_targets} detail="A8, G3, Desktop, AlphaMate, Claude, Codex" />
        </section>

        <section className="rounded-3xl border border-white/10 bg-[#0f1011]/80 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.32)] lg:p-5">
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="font-mono text-[10px] tracking-[0.22em] text-primary">MOBILE WORKSPACE</div>
              <h2 className="mt-2 font-expanded text-xl text-foreground">모바일 작업 홈</h2>
              <p className="mt-2 text-xs leading-5 text-muted-foreground normal-case">휴대폰에서 바로 작업을 시작하고, 진행 중인 세션을 이어가고, 승인 상태를 확인하는 Telegram 대체 홈입니다.</p>
            </div>
            <div className="flex items-center gap-2 rounded-full border border-success/30 bg-success/10 px-3 py-1 text-xs text-success">
              <CheckCircle2 className="h-3.5 w-3.5" /> 외부 접속 보호 확인
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <QuickAction icon={Play} title="새 작업 시작" detail="Hermes 채팅으로 이동해 새 지시를 입력합니다." href="/chat" tone="primary" />
            <QuickAction icon={MessagesSquare} title="최근 작업 이어가기" detail="최근 세션에서 대화를 다시 열고 흐름을 이어갑니다." href={overview.recent_sessions[0] ? `/chat?resume=${encodeURIComponent(overview.recent_sessions[0].id)}` : "/sessions"} />
            <QuickAction icon={Inbox} title="승인 대기" detail="위험 작업 승인 브리지는 다음 단계에서 연결합니다. 현재는 대기 없음 상태입니다." tone="warning" />
            <QuickAction icon={Network} title="인프라 상태" detail="A8·G3·Desktop·AlphaMate 제어 대상을 한눈에 확인합니다." tone="success" />
          </div>
        </section>

        <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <Card className="rounded-3xl border-white/10 bg-white/[0.035]">
            <CardHeader className="border-white/10">
              <CardTitle className="flex items-center gap-2"><Bot className="h-4 w-4" /> 에이전트 스택</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-3">
              {overview.agents.map((agent) => (
                <div key={agent.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-expanded text-sm text-foreground">{agent.label}</div>
                    <Badge variant={stateVariant(agent.state)}>{stateLabel(agent.state)}</Badge>
                  </div>
                  <p className="mt-3 text-xs leading-5 text-muted-foreground normal-case">{agent.detail}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-white/10 bg-white/[0.035]">
            <CardHeader className="border-white/10">
              <CardTitle className="flex items-center gap-2"><ShieldCheck className="h-4 w-4" /> 게이트웨이 상태</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm normal-case">
              <div className="flex justify-between rounded-xl bg-black/20 px-3 py-2"><span className="text-muted-foreground">상태</span><Badge variant={stateVariant(overview.status.gateway_state || "unknown")}>{stateLabel(overview.status.gateway_state)}</Badge></div>
              <div className="flex justify-between rounded-xl bg-black/20 px-3 py-2"><span className="text-muted-foreground">PID</span><span>{overview.status.gateway_pid || "—"}</span></div>
              <div className="flex justify-between rounded-xl bg-black/20 px-3 py-2"><span className="text-muted-foreground">노출 방식</span><span>로컬/LAN 확인</span></div>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <Card className="rounded-3xl border-white/10 bg-white/[0.035]">
            <CardHeader className="border-white/10">
              <CardTitle className="flex items-center gap-2"><Server className="h-4 w-4" /> 제어 패널</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              {overview.control_panels.map((panel) => (
                <div key={panel.id} className="rounded-2xl border border-white/10 bg-black/20 p-4 transition-colors hover:bg-white/[0.04]">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-expanded text-xs text-foreground">{panel.label}</span>
                    <Badge variant={stateVariant(panel.state)}>{stateLabel(panel.state)}</Badge>
                  </div>
                  <p className="mt-3 text-xs leading-5 text-muted-foreground normal-case">{panel.role}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-white/10 bg-white/[0.035]">
            <CardHeader className="border-white/10">
              <CardTitle className="flex items-center gap-2"><MessagesSquare className="h-4 w-4" /> 최근 작업</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {overview.recent_sessions.length ? (
                overview.recent_sessions.map((session) => <SessionRow key={session.id} session={session} />)
              ) : (
                <div className="py-8 text-center text-sm text-muted-foreground normal-case">최근 세션이 없습니다.</div>
              )}
            </CardContent>
          </Card>
        </section>

        <Card className="rounded-3xl border-white/10 bg-gradient-to-r from-white/[0.05] to-primary/10">
          <CardContent className="flex flex-col gap-3 p-5 text-sm text-muted-foreground normal-case md:flex-row md:items-center md:justify-between">
            <div className="flex items-start gap-3">
              <Rocket className="mt-0.5 h-4 w-4 text-primary" />
              <div>
                <div className="font-expanded text-xs text-foreground">다음 단계</div>
                <div className="mt-1 text-xs leading-5">채팅 입력, 승인 버튼, 작업 진행 상태, 파일·로그 드릴다운을 붙이면 Telegram 대체 콘솔로 넘어갈 수 있습니다.</div>
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <Boxes className="h-4 w-4" /> 샘플링 기반 재해석
              <ExternalLink className="h-3 w-3" /> 단순 복제 아님
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
