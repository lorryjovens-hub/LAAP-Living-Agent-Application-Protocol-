//! LAAP Core — Memory, Growth & Agent Engine
//! Rust-powered performance layer for the LAAP agent framework.
//!
//! Components:
//! - MemoryEngine: concurrent memory store with vector search
//! - ExperienceGraph: experience consolidation and pattern extraction
//! - TokenCounter: fast LLM token estimation
//! - SessionState: concurrent session management
//! - EmbeddingEngine: fast local embeddings via fastembed
//! - RegexCache: compiled regex cache for search patterns
//! - KeywordSearch: fast keyword-based document search

use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::exceptions::{PyRuntimeError, PyKeyError, PyValueError};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::sync::{Arc, Mutex, RwLock};
use std::time::{SystemTime, UNIX_EPOCH};

// ═══════════════════════════════════════════════════════
// Token Counter
// ═══════════════════════════════════════════════════════

#[pyclass]
pub struct TokenCounter {
    chars_per_token: f64,
}

#[pymethods]
impl TokenCounter {
    #[new]
    pub fn new(chars_per_token: Option<f64>) -> Self {
        TokenCounter { chars_per_token: chars_per_token.unwrap_or(4.0) }
    }

    pub fn count(&self, text: &str) -> usize {
        (text.len() as f64 / self.chars_per_token).ceil() as usize
    }

    pub fn count_messages(&self, messages: &PyDict) -> PyResult<usize> {
        let mut total = 0;
        for (k, v) in messages.iter() {
            total += self.count(&k.extract::<String>()?);
            total += self.count(&v.extract::<String>()?);
        }
        Ok(total)
    }
}

// ═══════════════════════════════════════════════════════
// Memory types
// ═══════════════════════════════════════════════════════

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct MemoryEntry {
    pub id: String,
    pub content: String,
    pub memory_type: String,
    pub importance: f32,
    pub timestamp: f64,
    pub access_count: u32,
    pub tags: Vec<String>,
    pub embedding: Option<Vec<f32>>,
    pub source: String,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct ExperienceEntry {
    pub id: String,
    pub pattern: String,
    pub context: String,
    pub outcome: String,
    pub success: bool,
    pub reinforcement: u32,
    pub generalizations: Vec<String>,
    pub timestamp: f64,
}

// ═══════════════════════════════════════════════════════
// Memory Engine — Concurrent + Vector Hybrid
// ═══════════════════════════════════════════════════════

#[pyclass]
pub struct MemoryEngine {
    dimension: usize,
    entries: Arc<RwLock<Vec<MemoryEntry>>>,
    recall_log: Arc<Mutex<VecDeque<String>>>,
    max_entries: usize,
}

#[pymethods]
impl MemoryEngine {
    #[new]
    pub fn new(dimension: Option<usize>, max_entries: Option<usize>) -> Self {
        MemoryEngine {
            dimension: dimension.unwrap_or(384),
            entries: Arc::new(RwLock::new(Vec::new())),
            recall_log: Arc::new(Mutex::new(VecDeque::with_capacity(100))),
            max_entries: max_entries.unwrap_or(10000),
        }
    }

    pub fn store(&self, id: &str, content: &str, memory_type: &str,
                 importance: f32, tags: Vec<String>, source: &str) -> PyResult<()> {
        let now = SystemTime::now().duration_since(UNIX_EPOCH)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?
            .as_secs_f64();
        let mut entries = self.entries.write()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?;

        if entries.len() >= self.max_entries {
            entries.sort_by(|a, b| a.importance.partial_cmp(&b.importance)
                .unwrap_or(std::cmp::Ordering::Equal));
            let excess = entries.len().saturating_sub(self.max_entries);
            if excess > 0 {
                entries.drain(0..excess);
            }
        }

        entries.push(MemoryEntry {
            id: id.to_string(),
            content: content.to_string(),
            memory_type: memory_type.to_string(),
            importance,
            timestamp: now,
            access_count: 0,
            tags,
            embedding: None,
            source: source.to_string(),
        });
        Ok(())
    }

    #[pyo3(signature = (query, memory_type=None, tags=None, limit=10))]
    pub fn recall(&self, query: &str, memory_type: Option<&str>,
                  tags: Option<Vec<String>>, limit: usize) -> PyResult<Vec<String>> {
        let entries = self.entries.read()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?;

        let query_lower = query.to_lowercase();
        let mut scored: Vec<(f32, &MemoryEntry)> = entries.iter()
            .filter(|e| {
                if let Some(mt) = memory_type {
                    if e.memory_type != mt { return false; }
                }
                if let Some(ref ts) = tags {
                    if !ts.iter().any(|t| e.tags.contains(t)) { return false; }
                }
                true
            })
            .map(|e| {
                let mut score = e.importance * 0.4;
                let now = SystemTime::now().duration_since(UNIX_EPOCH)
                    .map(|d| d.as_secs_f64()).unwrap_or(0.0);
                let recency = (now - e.timestamp) / 3600.0;
                score += (1.0 / (recency + 1.0)) as f32 * 0.3;
                if e.content.to_lowercase().contains(&query_lower) { score += 0.3; }
                score += (e.access_count as f32) * 0.01;
                (score, e)
            })
            .collect();

        scored.sort_by(|a, b| b.0.partial_cmp(&a.0)
            .unwrap_or(std::cmp::Ordering::Equal));

        if let Ok(mut log) = self.recall_log.lock() {
            log.push_back(query.to_string());
            if log.len() > 100 { log.pop_front(); }
        }

        Ok(scored.into_iter().take(limit).map(|(_, e)| {
            format!("[{}] {} (imp:{:.2})", e.memory_type, e.content, e.importance)
        }).collect())
    }

    pub fn search_similar(&self, query_embedding: Vec<f32>, top_k: usize) -> PyResult<Vec<(String, f32)>> {
        let entries = self.entries.read()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?;

        let qnorm: f32 = query_embedding.iter().map(|x| x*x).sum::<f32>().sqrt();
        if qnorm == 0.0 { return Ok(Vec::new()); }

        let mut results: Vec<(String, f32)> = entries.iter()
            .filter(|e| e.embedding.is_some())
            .map(|e| {
                let emb = e.embedding.as_ref().unwrap();
                let dot: f32 = query_embedding.iter().zip(emb.iter()).map(|(a,b)| a*b).sum();
                let enorm: f32 = emb.iter().map(|x| x*x).sum::<f32>().sqrt();
                (e.id.clone(), dot / (qnorm * enorm))
            })
            .collect();

        results.sort_by(|a, b| b.1.partial_cmp(&a.1)
            .unwrap_or(std::cmp::Ordering::Equal));
        results.truncate(top_k);
        Ok(results)
    }

    pub fn stats(&self) -> PyResult<Vec<(String, usize)>> {
        let entries = self.entries.read()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?;
        let mut by_type: HashMap<String, usize> = HashMap::new();
        for e in entries.iter() {
            *by_type.entry(e.memory_type.clone()).or_insert(0) += 1;
        }
        let mut result: Vec<_> = by_type.into_iter().collect();
        result.sort();
        result.push(("total".to_string(), entries.len()));
        Ok(result)
    }

    pub fn len(&self) -> usize {
        self.entries.read().map(|e| e.len()).unwrap_or(0)
    }
}

// ═══════════════════════════════════════════════════════
// Experience Graph — Growth & Learning
// ═══════════════════════════════════════════════════════

#[pyclass]
pub struct ExperienceGraph {
    experiences: Arc<RwLock<Vec<ExperienceEntry>>>,
    pattern_index: Arc<RwLock<HashMap<String, Vec<usize>>>>,
}

#[pymethods]
impl ExperienceGraph {
    #[new]
    pub fn new() -> Self {
        ExperienceGraph {
            experiences: Arc::new(RwLock::new(Vec::new())),
            pattern_index: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn record(&self, pattern: &str, context: &str, outcome: &str,
                  success: bool, id: Option<&str>) -> PyResult<String> {
        let uid = id.unwrap_or("").to_string();
        let uid = if uid.is_empty() {
            format!("exp_{}", SystemTime::now().duration_since(UNIX_EPOCH)
                .map(|d| d.as_nanos()).unwrap_or(0))
        } else { uid };

        let entry = ExperienceEntry {
            id: uid.clone(),
            pattern: pattern.to_string(),
            context: context.to_string(),
            outcome: outcome.to_string(),
            success,
            reinforcement: 1,
            generalizations: Vec::new(),
            timestamp: SystemTime::now().duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64()).unwrap_or(0.0),
        };

        if let Ok(mut exps) = self.experiences.write() {
            let pattern_lower = pattern.to_lowercase();
            for exp in exps.iter_mut() {
                if exp.pattern.to_lowercase() == pattern_lower && exp.context == context {
                    exp.reinforcement += 1;
                    exp.success = exp.success || success;
                    return Ok(format!("reinforced:{}", exp.id));
                }
            }
            exps.push(entry);
        }

        if let Ok(mut idx) = self.pattern_index.write() {
            idx.entry(pattern.to_string()).or_insert_with(Vec::new).push(
                self.experiences.read().map(|e| e.len().saturating_sub(1)).unwrap_or(0)
            );
        }
        Ok(format!("recorded:{}", uid))
    }

    pub fn recall_experiences(&self, context: &str, top_k: usize) -> PyResult<Vec<String>> {
        let exps = self.experiences.read()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?;
        let ctx_lower = context.to_lowercase();

        let mut scored: Vec<(f32, &ExperienceEntry)> = exps.iter()
            .map(|e| {
                let mut score = if e.success { 0.5 } else { 0.2 };
                score += (e.reinforcement as f32) * 0.1;
                if e.context.to_lowercase().contains(&ctx_lower) { score += 0.3; }
                if e.pattern.to_lowercase().contains(&ctx_lower) { score += 0.2; }
                (score, e)
            })
            .collect();

        scored.sort_by(|a, b| b.0.partial_cmp(&a.0)
            .unwrap_or(std::cmp::Ordering::Equal));

        Ok(scored.into_iter().take(top_k).map(|(s, e)| {
            format!("[{}] {} -> {} (reinforced:{}x, success:{})",
                    e.id, e.pattern, e.outcome, e.reinforcement, e.success)
        }).collect())
    }

    pub fn consolidate(&self) -> PyResult<Vec<String>> {
        let exps = self.experiences.read()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?;

        let mut pattern_groups: HashMap<String, Vec<&ExperienceEntry>> = HashMap::new();
        for exp in exps.iter() {
            pattern_groups.entry(exp.pattern.clone()).or_insert_with(Vec::new).push(exp);
        }

        let mut generalizations = Vec::new();
        for (pattern, group) in &pattern_groups {
            if group.len() >= 3 {
                let _avg_success = group.iter().filter(|e| e.success).count() as f32 / group.len() as f32;
                let total_reinf: u32 = group.iter().map(|e| e.reinforcement).sum();
                generalizations.push(format!(
                    "Generalized: '{}' ({}/{} success, {} total reinforcements)",
                    pattern,
                    group.iter().filter(|e| e.success).count(),
                    group.len(),
                    total_reinf,
                ));
            }
        }
        Ok(generalizations)
    }

    pub fn experience_count(&self) -> usize {
        self.experiences.read().map(|e| e.len()).unwrap_or(0)
    }
}

// ═══════════════════════════════════════════════════════
// Fast Keyword Search Engine
// ═══════════════════════════════════════════════════════

#[pyclass]
pub struct KeywordSearch {
    documents: Arc<RwLock<Vec<String>>>,
    doc_ids: Arc<RwLock<Vec<String>>>,
}

#[pymethods]
impl KeywordSearch {
    #[new]
    pub fn new() -> Self {
        KeywordSearch {
            documents: Arc::new(RwLock::new(Vec::new())),
            doc_ids: Arc::new(RwLock::new(Vec::new())),
        }
    }

    pub fn index(&self, id: &str, text: &str) -> PyResult<()> {
        self.documents.write()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?
            .push(text.to_string());
        self.doc_ids.write()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?
            .push(id.to_string());
        Ok(())
    }

    pub fn search(&self, query: &str, top_k: usize) -> PyResult<Vec<(String, String, f32)>> {
        let docs = self.documents.read()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?;
        let ids = self.doc_ids.read()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?;
        let query_lower = query.to_lowercase();
        let query_words: Vec<&str> = query_lower.split_whitespace().collect();

        let mut scored: Vec<(usize, f32)> = docs.iter().enumerate().map(|(i, doc)| {
            let doc_lower = doc.to_lowercase();
            let mut score = 0.0f32;
            for word in &query_words {
                if doc_lower.contains(word) {
                    score += 1.0;
                }
            }
            // Exact phrase match bonus
            if doc_lower.contains(&query_lower) {
                score += 3.0;
            }
            (i, score)
        }).collect();

        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scored.truncate(top_k);

        Ok(scored.into_iter().filter(|(_, s)| *s > 0.0).map(|(i, s)| {
            (ids[i].clone(), docs[i].chars().take(200).collect::<String>(), s)
        }).collect())
    }

    pub fn clear(&self) -> PyResult<()> {
        self.documents.write()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?
            .clear();
        self.doc_ids.write()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?
            .clear();
        Ok(())
    }

    pub fn doc_count(&self) -> usize {
        self.documents.read().map(|d| d.len()).unwrap_or(0)
    }
}

// ═══════════════════════════════════════════════════════
// Session State Manager
// ═══════════════════════════════════════════════════════

#[derive(Clone, Serialize, Deserialize)]
struct SessionRecord {
    id: String,
    parent_id: String,
    turn_count: u64,
    token_count: u64,
    created_at: f64,
    state: String,
    metadata: HashMap<String, String>,
}

#[pyclass]
pub struct SessionManager {
    sessions: Arc<RwLock<HashMap<String, SessionRecord>>>,
}

#[pymethods]
impl SessionManager {
    #[new]
    pub fn new() -> Self {
        SessionManager { sessions: Arc::new(RwLock::new(HashMap::new())) }
    }

    pub fn create(&self, session_id: &str, parent_id: Option<&str>) -> PyResult<bool> {
        let mut sessions = self.sessions.write()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?;
        if sessions.contains_key(session_id) { return Ok(false); }
        sessions.insert(session_id.to_string(), SessionRecord {
            id: session_id.to_string(),
            parent_id: parent_id.unwrap_or("").to_string(),
            turn_count: 0, token_count: 0,
            created_at: SystemTime::now().duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64()).unwrap_or(0.0),
            state: "active".to_string(),
            metadata: HashMap::new(),
        });
        Ok(true)
    }

    pub fn get_info(&self, session_id: &str) -> PyResult<String> {
        let sessions = self.sessions.read()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?;
        match sessions.get(session_id) {
            Some(s) => Ok(serde_json::to_string(s).unwrap_or_default()),
            None => Err(PyKeyError::new_err(format!("Session not found: {}", session_id))),
        }
    }

    pub fn list_active(&self) -> Vec<(String, u64, u64)> {
        self.sessions.read().map(|s| {
            s.iter().filter(|(_, r)| r.state == "active")
             .map(|(id, r)| (id.clone(), r.turn_count, r.token_count))
             .collect()
        }).unwrap_or_default()
    }

    pub fn add_tokens(&self, session_id: &str, tokens: u64) -> PyResult<u64> {
        let mut sessions = self.sessions.write()
            .map_err(|e| PyRuntimeError::new_err(format!("Lock: {}", e)))?;
        match sessions.get_mut(session_id) {
            Some(s) => { s.turn_count += 1; s.token_count += tokens; Ok(s.token_count) },
            None => Err(PyKeyError::new_err(format!("Session not found: {}", session_id))),
        }
    }
}

// ═══════════════════════════════════════════════════════
// Module Registration
// ═══════════════════════════════════════════════════════

#[pymodule]
fn laap_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<TokenCounter>()?;
    m.add_class::<MemoryEngine>()?;
    m.add_class::<ExperienceGraph>()?;
    m.add_class::<KeywordSearch>()?;
    m.add_class::<SessionManager>()?;
    m.add("__version__", "0.3.0")?;
    Ok(())
}
