use crate::models::{AppData, EventRecord, HeatmapDay, MetricsSummary, SubjectMetric};
use chrono::{Duration, Local, NaiveDate, NaiveDateTime};
use std::collections::{BTreeMap, HashMap};

fn parse_event_date(ts: &str) -> Option<NaiveDate> {
    if ts.len() >= 10 {
        if let Ok(d) = NaiveDate::parse_from_str(&ts[..10], "%Y-%m-%d") {
            return Some(d);
        }
    }
    NaiveDateTime::parse_from_str(ts, "%Y-%m-%dT%H:%M:%S")
        .ok()
        .map(|dt| dt.date())
}

#[derive(Default)]
struct DayBucket {
    questions: u32,
    reading_min: u32,
    focus_min: u32,
    project_min: u32,
}

impl DayBucket {
    fn activity_score(&self) -> u32 {
        // Reading weighted strongly to reinforce consistent reading habits alongside exercises
        self.questions * 8 + self.reading_min + (self.focus_min / 2) + (self.project_min / 2)
    }

    fn is_active(&self) -> bool {
        self.questions > 0 || self.reading_min >= 10 || self.focus_min >= 15 || self.project_min >= 15
    }
}

pub fn compute_metrics(data: &AppData, events: &[EventRecord]) -> MetricsSummary {
    let today = Local::now().date_naive();
    let today_str = today.format("%Y-%m-%d").to_string();
    let heatmap_days: i64 = 112; // 16 weeks
    let start_heatmap = today - Duration::days(heatmap_days - 1);
    let week_start = today - Duration::days(6);
    let days_30_start = today - Duration::days(29);

    let mut daily: BTreeMap<NaiveDate, DayBucket> = BTreeMap::new();
    let mut subj_week_q: HashMap<String, u32> = HashMap::new();
    let mut subj_week_r: HashMap<String, u32> = HashMap::new();
    let mut subj_week_s: HashMap<String, u32> = HashMap::new();
    let mut subj_last_study: HashMap<String, NaiveDate> = HashMap::new();
    let mut subj_last_reading: HashMap<String, NaiveDate> = HashMap::new();

    for ev in events {
        let Some(raw_ts) = ev.effective_ts() else {
            continue;
        };
        let Some(date) = parse_event_date(raw_ts) else {
            continue;
        };

        let q = ev.questions.unwrap_or(0);
        let r = ev.reading_min.unwrap_or(0);
        let dur = ev.duration_min.unwrap_or(0);

        let bucket = daily.entry(date).or_default();
        match ev.event_type.as_str() {
            "study_session" | "study" => {
                bucket.questions += q;
                bucket.reading_min += r;
                bucket.focus_min += if dur > 0 { dur } else { r };
            }
            "question_attempt" => {
                bucket.questions += 1;
            }
            "focus_session" => {
                bucket.focus_min += dur;
                if ev.mode.as_deref() == Some("leitura") {
                    bucket.reading_min += dur;
                }
            }
            "project_session" => {
                bucket.project_min += if dur > 0 { dur } else { 30 };
            }
            _ => {}
        }

        if let Some(subj) = ev.subject.as_ref() {
            let sid = subj.to_lowercase();
            let entry_s = subj_last_study.entry(sid.clone()).or_insert(date);
            if date > *entry_s {
                *entry_s = date;
            }
            if r > 0 || ev.mode.as_deref() == Some("leitura") {
                let entry_r = subj_last_reading.entry(sid.clone()).or_insert(date);
                if date > *entry_r {
                    *entry_r = date;
                }
            }
            if date >= week_start && date <= today {
                let add_q = if ev.event_type == "question_attempt" { 1 } else { q };
                *subj_week_q.entry(sid.clone()).or_insert(0) += add_q;
                let add_r = if ev.event_type == "focus_session" && ev.mode.as_deref() == Some("leitura") {
                    dur
                } else {
                    r
                };
                *subj_week_r.entry(sid.clone()).or_insert(0) += add_r;
                if matches!(ev.event_type.as_str(), "study_session" | "study" | "focus_session") {
                    *subj_week_s.entry(sid).or_insert(0) += 1;
                }
            }
        }
    }

    // Build 112-day heatmap
    let mut heatmap = Vec::with_capacity(heatmap_days as usize);
    let mut active_days_30d: u32 = 0;
    let mut week_questions: u32 = 0;
    let mut week_reading_min: u32 = 0;
    let mut week_project_min: u32 = 0;

    for offset in 0..heatmap_days {
        let d = start_heatmap + Duration::days(offset);
        let b = daily.get(&d);
        let (q, r, f, p, score) = match b {
            Some(bucket) => (
                bucket.questions,
                bucket.reading_min,
                bucket.focus_min,
                bucket.project_min,
                bucket.activity_score(),
            ),
            None => (0, 0, 0, 0, 0),
        };
        let level = match score {
            0 => 0,
            1..=25 => 1,
            26..=60 => 2,
            61..=110 => 3,
            _ => 4,
        };
        if d >= days_30_start && d <= today && b.map(|x| x.is_active()).unwrap_or(false) {
            active_days_30d += 1;
        }
        if d >= week_start && d <= today {
            week_questions += q;
            week_reading_min += r;
            week_project_min += p;
        }
        heatmap.push(HeatmapDay {
            date: d.format("%Y-%m-%d").to_string(),
            questions: q,
            reading_min: r,
            focus_min: f,
            project_min: p,
            score,
            level,
        });
    }

    // Current streak (allowing today to still be in progress if yesterday was active)
    let mut current_streak: u32 = 0;
    let mut cursor = today;
    if !daily.get(&today).map(|b| b.is_active()).unwrap_or(false) {
        cursor = today - Duration::days(1);
    }
    while daily.get(&cursor).map(|b| b.is_active()).unwrap_or(false) {
        current_streak += 1;
        cursor -= Duration::days(1);
    }

    // Best streak across recorded history
    let mut best_streak: u32 = current_streak;
    let mut run: u32 = 0;
    let mut prev_day: Option<NaiveDate> = None;
    for (d, b) in &daily {
        if !b.is_active() {
            continue;
        }
        if let Some(prev) = prev_day {
            if *d == prev + Duration::days(1) {
                run += 1;
            } else {
                run = 1;
            }
        } else {
            run = 1;
        }
        if run > best_streak {
            best_streak = run;
        }
        prev_day = Some(*d);
    }

    let today_bucket = daily.get(&today);
    let today_questions = today_bucket.map(|b| b.questions).unwrap_or(0);
    let today_reading_min = today_bucket.map(|b| b.reading_min).unwrap_or(0);
    let today_focus_min = today_bucket.map(|b| b.focus_min).unwrap_or(0);
    let today_project_min = today_bucket.map(|b| b.project_min).unwrap_or(0);

    // Reading vs Exercise balance ratio (0..100% reading share in weekly study effort)
    let exercise_equiv_min = week_questions * 10;
    let total_study_effort = week_reading_min + exercise_equiv_min;
    let reading_ratio_pct = if total_study_effort > 0 {
        ((week_reading_min as f64 / total_study_effort as f64) * 100.0).round() as u32
    } else {
        0
    };

    // Consistency score (0..100):
    // 45% active days in last 14d, 30% weekly reading goal, 25% weekly questions goal
    let active_14d = (0..14)
        .filter(|i| {
            let d = today - Duration::days(*i);
            daily.get(&d).map(|b| b.is_active()).unwrap_or(false)
        })
        .count() as f64;
    let freq_part = (active_14d / 14.0).min(1.0) * 45.0;
    let weekly_r_goal = (data.daily_goals.leitura_min.max(1) * 5) as f64;
    let weekly_q_goal = (data.daily_goals.questoes.max(1) * 5) as f64;
    let read_part = (week_reading_min as f64 / weekly_r_goal).min(1.0) * 30.0;
    let quest_part = (week_questions as f64 / weekly_q_goal).min(1.0) * 25.0;
    let consistency_score = (freq_part + read_part + quest_part).round().min(100.0) as u32;

    // Subject metrics for active semester
    let mut subject_metrics = Vec::new();
    if let Some(sem) = data.semesters.get(&data.active_semester) {
        for s in &sem.disciplinas {
            let sid = s.id.to_lowercase();
            let last_s = subj_last_study
                .get(&sid)
                .copied()
                .or_else(|| s.ultimo_estudo.as_deref().and_then(parse_event_date));
            let last_r = subj_last_reading
                .get(&sid)
                .copied()
                .or_else(|| s.ultima_leitura.as_deref().and_then(parse_event_date));

            let days_since_study = last_s.map(|d| (today - d).num_days().max(0));
            let days_since_reading = last_r.map(|d| (today - d).num_days().max(0));

            let total_topics = s.topicos.len() as u32;
            let reading_topics_done = s.topicos.iter().filter(|t| t.leitura_concluida).count() as u32;
            let weighted_done: f64 = s
                .topicos
                .iter()
                .map(|t| match t.status.as_str() {
                    "dominado" => 1.0,
                    "praticando" => 0.65,
                    "lendo" => 0.35,
                    _ => 0.0,
                })
                .sum();
            let syllabus_progress_pct = if total_topics > 0 {
                ((weighted_done / total_topics as f64) * 100.0).round() as u32
            } else {
                0
            };

            let neglected = match days_since_study {
                None => s.prioridade == "alta",
                Some(days) => days >= 4,
            };

            subject_metrics.push(SubjectMetric {
                subject_id: s.id.clone(),
                nome: s.nome.clone(),
                cor: s.cor.clone(),
                prioridade: s.prioridade.clone(),
                week_questions: *subj_week_q.get(&sid).unwrap_or(&0),
                week_reading_min: *subj_week_r.get(&sid).unwrap_or(&0),
                week_sessions: *subj_week_s.get(&sid).unwrap_or(&0),
                goal_questions: s.metas.questoes_semana,
                goal_reading_min: s.metas.leitura_min_semana,
                days_since_study,
                days_since_reading,
                syllabus_progress_pct,
                reading_topics_done,
                total_topics,
                neglected,
            });
        }
    }

    let mut recent_events: Vec<EventRecord> = events.iter().rev().take(25).cloned().collect();
    recent_events.truncate(25);

    MetricsSummary {
        today_date: today_str,
        today_questions,
        today_reading_min,
        today_focus_min,
        today_project_min,
        daily_goals: data.daily_goals.clone(),
        current_streak,
        best_streak,
        active_days_30d,
        consistency_score,
        week_questions,
        week_reading_min,
        week_project_min,
        reading_ratio_pct,
        heatmap,
        subject_metrics,
        recent_events,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{DailyGoals, Semester, Subject, SubjectGoals, SyllabusTopic};
    use std::collections::BTreeMap;

    fn sample_data() -> AppData {
        let mut semesters = BTreeMap::new();
        semesters.insert(
            "2027.1".to_string(),
            Semester {
                id: "2027.1".to_string(),
                nome: "2027.1".to_string(),
                status: "ativo".to_string(),
                inicio: None,
                fim: None,
                disciplinas: vec![
                    Subject {
                        id: "fisica3".to_string(),
                        nome: "Física III".to_string(),
                        codigo: "FIS03".to_string(),
                        categoria: "teorica".to_string(),
                        prioridade: "alta".to_string(),
                        cor: "#38bdf8".to_string(),
                        descricao: String::new(),
                        materiais_dir: "estudos/fisica3".to_string(),
                        questoes_file: "fisica3.json".to_string(),
                        metas: SubjectGoals {
                            questoes_semana: 10,
                            leitura_min_semana: 120,
                            sessoes_semana: 3,
                        },
                        avaliacoes: vec![],
                        topicos: vec![
                            SyllabusTopic {
                                id: "t1".to_string(),
                                titulo: "Gauss".to_string(),
                                status: "dominado".to_string(),
                                leitura_concluida: true,
                                questoes_resolvidas: 5,
                            },
                            SyllabusTopic {
                                id: "t2".to_string(),
                                titulo: "Faraday".to_string(),
                                status: "lendo".to_string(),
                                leitura_concluida: false,
                                questoes_resolvidas: 0,
                            },
                        ],
                        ultimo_estudo: None,
                        ultima_leitura: None,
                    },
                    Subject {
                        id: "eletromagnetismo".to_string(),
                        nome: "Eletromagnetismo".to_string(),
                        codigo: "ELETROMAG".to_string(),
                        categoria: "teorica".to_string(),
                        prioridade: "alta".to_string(),
                        cor: "#f472b6".to_string(),
                        descricao: String::new(),
                        materiais_dir: "estudos/eletromagnetismo".to_string(),
                        questoes_file: "eletromagnetismo.json".to_string(),
                        metas: SubjectGoals {
                            questoes_semana: 10,
                            leitura_min_semana: 100,
                            sessoes_semana: 3,
                        },
                        avaliacoes: vec![],
                        topicos: vec![],
                        ultimo_estudo: None,
                        ultima_leitura: None,
                    },
                ],
            },
        );
        AppData {
            schema_version: 2,
            active_semester: "2027.1".to_string(),
            daily_goals: DailyGoals {
                questoes: 5,
                leitura_min: 45,
                foco_min: 90,
            },
            agy_config: Default::default(),
            semesters,
            extra: BTreeMap::new(),
        }
    }

    fn make_study_event(days_ago: i64, subject: &str, questions: u32, reading_min: u32) -> EventRecord {
        let dt = Local::now().date_naive() - Duration::days(days_ago);
        EventRecord {
            ts: Some(format!("{}T10:00:00", dt.format("%Y-%m-%d"))),
            timestamp: None,
            env: Some("test".to_string()),
            event_type: "study_session".to_string(),
            subject: Some(subject.to_string()),
            project: None,
            category: None,
            questions: Some(questions),
            reading_min: Some(reading_min),
            pages: Some(5),
            duration_min: Some(reading_min),
            mode: Some("misto".to_string()),
            topic: Some("Gauss".to_string()),
            result: None,
            summary: None,
            question_id: None,
        }
    }

    #[test]
    fn computes_streak_heatmap_and_reading_balance() {
        let data = sample_data();
        let events = vec![
            make_study_event(2, "fisica3", 3, 30),
            make_study_event(1, "fisica3", 4, 45),
            make_study_event(0, "fisica3", 5, 50),
        ];

        let summary = compute_metrics(&data, &events);
        assert_eq!(summary.heatmap.len(), 112);
        assert_eq!(summary.current_streak, 3);
        assert_eq!(summary.best_streak, 3);
        assert_eq!(summary.today_questions, 5);
        assert_eq!(summary.today_reading_min, 50);
        assert_eq!(summary.week_questions, 12);
        assert_eq!(summary.week_reading_min, 125);
        assert!(summary.reading_ratio_pct > 45 && summary.reading_ratio_pct < 60);
        assert!(summary.consistency_score >= 35 && summary.consistency_score <= 45);
    }

    #[test]
    fn detects_neglected_subjects_and_syllabus_progress() {
        let data = sample_data();
        let events = vec![make_study_event(0, "fisica3", 2, 30)];

        let summary = compute_metrics(&data, &events);
        let f3 = summary
            .subject_metrics
            .iter()
            .find(|s| s.subject_id == "fisica3")
            .unwrap();
        let em = summary
            .subject_metrics
            .iter()
            .find(|s| s.subject_id == "eletromagnetismo")
            .unwrap();

        assert!(!f3.neglected);
        assert_eq!(f3.days_since_study, Some(0));
        assert_eq!(f3.reading_topics_done, 1);
        assert_eq!(f3.total_topics, 2);
        // (1.0 + 0.35) / 2 = 67.5 -> 68%
        assert_eq!(f3.syllabus_progress_pct, 68);

        assert!(em.neglected);
        assert_eq!(em.days_since_study, None);
    }

    #[test]
    fn preserves_streak_if_yesterday_was_active_and_today_not_yet() {
        let data = sample_data();
        let events = vec![
            make_study_event(2, "fisica3", 2, 20),
            make_study_event(1, "fisica3", 2, 20),
        ];
        let summary = compute_metrics(&data, &events);
        assert_eq!(summary.current_streak, 2);
        assert_eq!(summary.today_questions, 0);
    }
}

