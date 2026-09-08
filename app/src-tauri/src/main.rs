#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{fs, sync::Mutex};

use chrono::Utc;
use csv::Writer;
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tauri::{Manager, State};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ProfileRecord {
    id: String,
    name: String,
    expected_groups: Vec<Vec<String>>,
    created_at: String,
    updated_at: String,
    notes: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ScanReportRecord {
    id: String,
    profile_id: Option<String>,
    profile_name: String,
    mode: String,
    comparison: Value,
    observation: Value,
    created_at: String,
    hardware_revision: String,
    firmware_version: String,
    limits_revision: String,
    protocol_major: i64,
    protocol_minor: i64,
    precheck_passed: bool,
    self_test_passed: bool,
    notes: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct BackupPayload {
    schema_version: u32,
    exported_at: String,
    profiles: Vec<ProfileRecord>,
    reports: Vec<ScanReportRecord>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
struct BackupPayloadIn {
    schema_version: u32,
    profiles: Vec<ProfileRecord>,
    reports: Vec<ScanReportRecord>,
}

#[derive(Debug, Clone, Serialize)]
struct ImportSummary {
    profiles: usize,
    reports: usize,
}

struct AppState {
    connection: Mutex<Connection>,
}

fn sanitize_text(input: &str) -> String {
    input
        .chars()
        .map(|ch| if ch.is_control() { ' ' } else { ch })
        .collect::<String>()
        .replace(['<', '>'], "")
}

fn open_connection(app: &tauri::AppHandle) -> Result<Connection, String> {
    let app_data_dir = app
        .path()
        .app_data_dir()
        .map_err(|err| format!("could not resolve app data directory: {err}"))?;
    fs::create_dir_all(&app_data_dir)
        .map_err(|err| format!("failed to create app data directory: {err}"))?;

    let db_path = app_data_dir.join("pinpath-companion.sqlite3");
    let conn = Connection::open(db_path).map_err(|err| format!("failed to open sqlite db: {err}"))?;
    run_migrations(&conn)?;
    Ok(conn)
}

fn run_migrations(conn: &Connection) -> Result<(), String> {
    conn.execute_batch(
        r#"
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS profiles (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          expected_groups_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          notes TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reports (
          id TEXT PRIMARY KEY,
          profile_id TEXT,
          profile_name TEXT NOT NULL,
          mode TEXT NOT NULL,
          comparison_json TEXT NOT NULL,
          observation_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          hardware_revision TEXT NOT NULL,
          firmware_version TEXT NOT NULL,
          limits_revision TEXT NOT NULL,
          protocol_major INTEGER NOT NULL,
          protocol_minor INTEGER NOT NULL,
          precheck_passed INTEGER NOT NULL,
          self_test_passed INTEGER NOT NULL,
          notes TEXT NOT NULL,
          FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE SET NULL
        );
        "#,
    )
    .map_err(|err| format!("migration failed: {err}"))?;

    Ok(())
}

fn parse_json_field<T: for<'de> Deserialize<'de>>(raw: String, field_name: &str) -> Result<T, String> {
    serde_json::from_str(&raw).map_err(|err| format!("invalid JSON in '{field_name}': {err}"))
}

fn as_json_string<T: Serialize>(value: &T, field_name: &str) -> Result<String, String> {
    serde_json::to_string(value).map_err(|err| format!("failed to serialize {field_name}: {err}"))
}

#[tauri::command]
fn list_profiles(state: State<'_, AppState>) -> Result<Vec<ProfileRecord>, String> {
    let conn = state.connection.lock().map_err(|_| "database mutex poisoned".to_string())?;
    let mut stmt = conn
        .prepare(
            "SELECT id, name, expected_groups_json, created_at, updated_at, notes FROM profiles ORDER BY updated_at DESC",
        )
        .map_err(|err| format!("failed to prepare profile query: {err}"))?;

    let iter = stmt
        .query_map([], |row| {
            let expected_raw: String = row.get(2)?;
            let expected_groups: Vec<Vec<String>> = serde_json::from_str(&expected_raw).unwrap_or_default();
            Ok(ProfileRecord {
                id: row.get(0)?,
                name: row.get(1)?,
                expected_groups,
                created_at: row.get(3)?,
                updated_at: row.get(4)?,
                notes: row.get(5)?,
            })
        })
        .map_err(|err| format!("failed to read profiles: {err}"))?;

    let mut profiles = Vec::new();
    for profile in iter {
        profiles.push(profile.map_err(|err| format!("profile row decode failed: {err}"))?);
    }
    Ok(profiles)
}

#[tauri::command]
fn upsert_profile(profile: ProfileRecord, state: State<'_, AppState>) -> Result<ProfileRecord, String> {
    let conn = state.connection.lock().map_err(|_| "database mutex poisoned".to_string())?;
    let expected_json = as_json_string(&profile.expected_groups, "expected_groups")?;

    conn.execute(
        r#"
        INSERT INTO profiles (id, name, expected_groups_json, created_at, updated_at, notes)
        VALUES (?1, ?2, ?3, ?4, ?5, ?6)
        ON CONFLICT(id) DO UPDATE SET
          name=excluded.name,
          expected_groups_json=excluded.expected_groups_json,
          updated_at=excluded.updated_at,
          notes=excluded.notes
        "#,
        params![
            profile.id,
            sanitize_text(&profile.name),
            expected_json,
            profile.created_at,
            profile.updated_at,
            sanitize_text(&profile.notes)
        ],
    )
    .map_err(|err| format!("failed to upsert profile: {err}"))?;

    Ok(profile)
}

#[tauri::command]
fn delete_profile(profile_id: String, state: State<'_, AppState>) -> Result<(), String> {
    let conn = state.connection.lock().map_err(|_| "database mutex poisoned".to_string())?;
    conn.execute("DELETE FROM profiles WHERE id = ?1", params![profile_id])
        .map_err(|err| format!("failed to delete profile: {err}"))?;
    Ok(())
}

#[tauri::command]
fn list_reports(state: State<'_, AppState>) -> Result<Vec<ScanReportRecord>, String> {
    let conn = state.connection.lock().map_err(|_| "database mutex poisoned".to_string())?;
    let mut stmt = conn
        .prepare(
            "SELECT id, profile_id, profile_name, mode, comparison_json, observation_json, created_at, hardware_revision, firmware_version, limits_revision, protocol_major, protocol_minor, precheck_passed, self_test_passed, notes FROM reports ORDER BY created_at DESC",
        )
        .map_err(|err| format!("failed to prepare report query: {err}"))?;

    let iter = stmt
        .query_map([], |row| {
            let comparison_raw: String = row.get(4)?;
            let observation_raw: String = row.get(5)?;
            let comparison: Value = serde_json::from_str(&comparison_raw).unwrap_or(Value::Null);
            let observation: Value = serde_json::from_str(&observation_raw).unwrap_or(Value::Null);
            Ok(ScanReportRecord {
                id: row.get(0)?,
                profile_id: row.get(1)?,
                profile_name: row.get(2)?,
                mode: row.get(3)?,
                comparison,
                observation,
                created_at: row.get(6)?,
                hardware_revision: row.get(7)?,
                firmware_version: row.get(8)?,
                limits_revision: row.get(9)?,
                protocol_major: row.get(10)?,
                protocol_minor: row.get(11)?,
                precheck_passed: row.get(12)?,
                self_test_passed: row.get(13)?,
                notes: row.get(14)?,
            })
        })
        .map_err(|err| format!("failed to read reports: {err}"))?;

    let mut reports = Vec::new();
    for report in iter {
        reports.push(report.map_err(|err| format!("report row decode failed: {err}"))?);
    }

    Ok(reports)
}

#[tauri::command]
fn upsert_report(report: ScanReportRecord, state: State<'_, AppState>) -> Result<ScanReportRecord, String> {
    let conn = state.connection.lock().map_err(|_| "database mutex poisoned".to_string())?;
    let comparison_json = as_json_string(&report.comparison, "comparison")?;
    let observation_json = as_json_string(&report.observation, "observation")?;

    conn.execute(
        r#"
        INSERT INTO reports (
          id, profile_id, profile_name, mode, comparison_json, observation_json, created_at,
          hardware_revision, firmware_version, limits_revision, protocol_major, protocol_minor,
          precheck_passed, self_test_passed, notes
        )
        VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15)
        ON CONFLICT(id) DO UPDATE SET
          profile_id=excluded.profile_id,
          profile_name=excluded.profile_name,
          mode=excluded.mode,
          comparison_json=excluded.comparison_json,
          observation_json=excluded.observation_json,
          created_at=excluded.created_at,
          hardware_revision=excluded.hardware_revision,
          firmware_version=excluded.firmware_version,
          limits_revision=excluded.limits_revision,
          protocol_major=excluded.protocol_major,
          protocol_minor=excluded.protocol_minor,
          precheck_passed=excluded.precheck_passed,
          self_test_passed=excluded.self_test_passed,
          notes=excluded.notes
        "#,
        params![
            report.id,
            report.profile_id,
            sanitize_text(&report.profile_name),
            sanitize_text(&report.mode),
            comparison_json,
            observation_json,
            report.created_at,
            sanitize_text(&report.hardware_revision),
            sanitize_text(&report.firmware_version),
            sanitize_text(&report.limits_revision),
            report.protocol_major,
            report.protocol_minor,
            report.precheck_passed,
            report.self_test_passed,
            sanitize_text(&report.notes)
        ],
    )
    .map_err(|err| format!("failed to upsert report: {err}"))?;

    Ok(report)
}

#[tauri::command]
fn delete_report(report_id: String, state: State<'_, AppState>) -> Result<(), String> {
    let conn = state.connection.lock().map_err(|_| "database mutex poisoned".to_string())?;
    conn.execute("DELETE FROM reports WHERE id = ?1", params![report_id])
        .map_err(|err| format!("failed to delete report: {err}"))?;
    Ok(())
}

#[tauri::command]
fn export_backup_json(state: State<'_, AppState>) -> Result<String, String> {
    let profiles = list_profiles(state.clone())?;
    let reports = list_reports(state)?;

    let payload = BackupPayload {
        schema_version: 1,
        exported_at: Utc::now().to_rfc3339(),
        profiles,
        reports,
    };

    serde_json::to_string_pretty(&payload).map_err(|err| format!("failed to serialize backup: {err}"))
}

#[tauri::command]
fn import_backup_json(json_payload: String, state: State<'_, AppState>) -> Result<ImportSummary, String> {
    let parsed: BackupPayloadIn = parse_json_field(json_payload, "backup payload")?;
    if parsed.schema_version != 1 {
        return Err(format!(
            "unsupported backup schema version {}; expected 1",
            parsed.schema_version
        ));
    }

    let conn = state.connection.lock().map_err(|_| "database mutex poisoned".to_string())?;
    let tx = conn
        .unchecked_transaction()
        .map_err(|err| format!("failed to start import transaction: {err}"))?;

    tx.execute("DELETE FROM reports", [])
        .map_err(|err| format!("failed to clear reports before import: {err}"))?;
    tx.execute("DELETE FROM profiles", [])
        .map_err(|err| format!("failed to clear profiles before import: {err}"))?;

    for profile in &parsed.profiles {
        let expected_json = as_json_string(&profile.expected_groups, "expected_groups")?;
        tx.execute(
            "INSERT INTO profiles (id, name, expected_groups_json, created_at, updated_at, notes) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![
                profile.id,
                sanitize_text(&profile.name),
                expected_json,
                profile.created_at,
                profile.updated_at,
                sanitize_text(&profile.notes)
            ],
        )
        .map_err(|err| format!("failed to insert profile during import: {err}"))?;
    }

    for report in &parsed.reports {
        let comparison_json = as_json_string(&report.comparison, "comparison")?;
        let observation_json = as_json_string(&report.observation, "observation")?;

        tx.execute(
            "INSERT INTO reports (id, profile_id, profile_name, mode, comparison_json, observation_json, created_at, hardware_revision, firmware_version, limits_revision, protocol_major, protocol_minor, precheck_passed, self_test_passed, notes) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15)",
            params![
                report.id,
                report.profile_id,
                sanitize_text(&report.profile_name),
                sanitize_text(&report.mode),
                comparison_json,
                observation_json,
                report.created_at,
                sanitize_text(&report.hardware_revision),
                sanitize_text(&report.firmware_version),
                sanitize_text(&report.limits_revision),
                report.protocol_major,
                report.protocol_minor,
                report.precheck_passed,
                report.self_test_passed,
                sanitize_text(&report.notes)
            ],
        )
        .map_err(|err| format!("failed to insert report during import: {err}"))?;
    }

    tx.commit()
        .map_err(|err| format!("failed to commit backup import: {err}"))?;

    Ok(ImportSummary {
        profiles: parsed.profiles.len(),
        reports: parsed.reports.len(),
    })
}

#[tauri::command]
fn export_reports_csv(state: State<'_, AppState>) -> Result<String, String> {
    let reports = list_reports(state)?;

    let mut writer = Writer::from_writer(vec![]);
    writer
        .write_record([
            "id",
            "created_at",
            "profile_name",
            "mode",
            "safe_to_proceed",
            "hardware_revision",
            "firmware_version",
            "limits_revision",
            "faults",
        ])
        .map_err(|err| format!("failed to write CSV header: {err}"))?;

    for report in reports {
        let safe_to_proceed = report
            .comparison
            .get("safeToProceed")
            .and_then(Value::as_bool)
            .unwrap_or(false)
            .to_string();

        let faults = report
            .observation
            .get("faults")
            .and_then(Value::as_array)
            .map(|arr| {
                arr.iter()
                    .filter_map(Value::as_str)
                    .map(sanitize_text)
                    .collect::<Vec<_>>()
                    .join(";")
            })
            .unwrap_or_default();

        writer
            .write_record([
                sanitize_text(&report.id),
                sanitize_text(&report.created_at),
                sanitize_text(&report.profile_name),
                sanitize_text(&report.mode),
                safe_to_proceed,
                sanitize_text(&report.hardware_revision),
                sanitize_text(&report.firmware_version),
                sanitize_text(&report.limits_revision),
                faults,
            ])
            .map_err(|err| format!("failed to write CSV row: {err}"))?;
    }

    let bytes = writer
        .into_inner()
        .map_err(|err| format!("failed to finalize CSV writer: {err}"))?;

    String::from_utf8(bytes).map_err(|err| format!("failed to encode CSV UTF-8 string: {err}"))
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let connection = open_connection(&app.handle())?;
            app.manage(AppState {
                connection: Mutex::new(connection),
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            list_profiles,
            upsert_profile,
            delete_profile,
            list_reports,
            upsert_report,
            delete_report,
            export_backup_json,
            import_backup_json,
            export_reports_csv
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
