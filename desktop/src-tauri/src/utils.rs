use std::path::{Path, Component};

const MAX_EXPORT_SIZE: usize = 10 * 1024 * 1024; // 10MB

#[tauri::command]
pub fn export_sql_to_txt(path: String, data: String) -> Result<String, String> {
    let file_path = Path::new(&path);

    // Prevent directory traversal
    if file_path.components().any(|c| matches!(c, Component::ParentDir)) {
        return Err("Invalid path: directory traversal not allowed".to_string());
    }

    // Validate extension
    match file_path.extension().and_then(|e| e.to_str()) {
        Some("txt") => {}
        _ => return Err("Only .txt files are allowed".to_string()),
    }

    // Check data size
    if data.len() > MAX_EXPORT_SIZE {
        return Err(format!("Data too large: {} bytes (max {})", data.len(), MAX_EXPORT_SIZE));
    }

    std::fs::write(file_path, data.as_bytes())
        .map(|_| "success 导出成功".to_string())
        .map_err(|e| format!("error: fail to export {}", e))
}
