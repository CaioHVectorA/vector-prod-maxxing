import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import type {
  AgyStatus,
  AppData,
  Evaluation,
  GitRepoInfo,
  HardwareSnapshot,
  MetricsSummary,
  ProjectItem,
  Question,
  StudyMaterial,
  Subject,
} from "./types";

export const isTauri = () =>
  typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

export const api = {
  getAppData: () => invoke<AppData>("get_app_data"),
  saveAppData: (data: AppData) => invoke<AppData>("save_app_data_cmd", { data }),
  setActiveSemester: (semesterId: string) =>
    invoke<AppData>("set_active_semester", { semesterId }),
  createSemester: (id: string, nome: string) =>
    invoke<AppData>("create_semester", { id, nome }),
  upsertSubject: (semesterId: string, subject: Subject) =>
    invoke<AppData>("upsert_subject", { semesterId, subject }),
  deleteSubject: (semesterId: string, subjectId: string) =>
    invoke<AppData>("delete_subject", { semesterId, subjectId }),
  updateTopicState: (
    semesterId: string,
    subjectId: string,
    topicId: string,
    status: string,
    leituraConcluida: boolean
  ) =>
    invoke<AppData>("update_topic_state", {
      semesterId,
      subjectId,
      topicId,
      status,
      leituraConcluida,
    }),
  addTopic: (semesterId: string, subjectId: string, titulo: string) =>
    invoke<AppData>("add_topic", { semesterId, subjectId, titulo }),
  updateEvaluations: (
    semesterId: string,
    subjectId: string,
    avaliacoes: Evaluation[]
  ) => invoke<AppData>("update_evaluations", { semesterId, subjectId, avaliacoes }),
  logStudySession: (payload: {
    subject_id: string;
    questions: number;
    reading_min: number;
    pages: number;
    duration_min: number;
    mode: string;
    topic: string;
  }) => invoke<MetricsSummary>("log_study_session", { payload }),
  getMetrics: () => invoke<MetricsSummary>("get_metrics"),
  getQuestions: (subjectId: string) =>
    invoke<Question[]>("get_questions", { subjectId }),
  recordQuestionAttempt: (payload: {
    subject_id: string;
    question_id: string;
    result: "acertei" | "errei" | "revisar";
  }) => invoke<Question[]>("record_question_attempt", { payload }),
  importQuestionsJson: (subjectId: string, rawJson: string) =>
    invoke<Question[]>("import_questions_json", { subjectId, rawJson }),
  listMaterials: (materiaisDir: string) =>
    invoke<StudyMaterial[]>("list_materials", { materiaisDir }),
  getProjects: () => invoke<ProjectItem[]>("get_projects"),
  saveProjects: (projects: ProjectItem[]) =>
    invoke<ProjectItem[]>("save_projects_cmd", { projects }),
  logProjectSession: (payload: {
    project_id: string;
    category: string;
    duration_min: number;
    summary: string;
    next_action?: string | null;
  }) => invoke<MetricsSummary>("log_project_session", { payload }),
  scanRepos: () => invoke<GitRepoInfo[]>("scan_repos"),
  scanHardware: () => invoke<HardwareSnapshot>("scan_hardware"),
  getAgyStatus: () => invoke<AgyStatus>("get_agy_status"),
  launchAgy: (workingDir?: string | null, prompt?: string | null) =>
    invoke<string>("launch_agy", { workingDir: workingDir ?? null, prompt: prompt ?? null }),
  openPath: (path: string) => invoke<void>("open_path", { path }),
  gitSyncNow: () => invoke<string>("git_sync_now"),
  onWorkspaceChanged: (cb: () => void): Promise<UnlistenFn> => {
    if (!isTauri()) return Promise.resolve(() => {});
    return listen("workspace-changed", () => cb());
  },
};

export async function copyToClipboard(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    // ignore clipboard fallback errors
  }
}
