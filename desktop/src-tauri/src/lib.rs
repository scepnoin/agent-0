use std::process::{Command, Stdio, Child};
use std::sync::Mutex;
use tauri::Manager;
#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

struct BackendState {
    process: Option<Child>,
    project_path: String,
}

#[tauri::command]
async fn pick_folder(app: tauri::AppHandle) -> Result<String, String> {
    use tauri_plugin_dialog::DialogExt;
    let result = app.dialog()
        .file()
        .set_title("Select Project Folder")
        .blocking_pick_folder();
    match result {
        Some(path) => Ok(path.to_string()),
        None => Err("No folder selected".to_string())
    }
}

#[tauri::command]
async fn switch_project(app: tauri::AppHandle, state: tauri::State<'_, Mutex<BackendState>>, path: String) -> Result<String, String> {
    let mut backend = state.lock().map_err(|e| e.to_string())?;

    // Kill ALL python processes running main.py (not just the tracked one)
    #[cfg(target_os = "windows")]
    {
        // Kill tracked process
        if let Some(ref mut child) = backend.process {
            let pid = child.id();
            let _ = Command::new("taskkill")
                .args(&["/F", "/T", "/PID", &pid.to_string()])
                .creation_flags(0x08000000)
                .output();
            let _ = child.wait();
        }
        // Also kill any other python processes on port 7800
        let _ = Command::new("cmd")
            .args(&["/C", "for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :7800 ^| findstr LISTENING') do taskkill /F /PID %a"])
            .creation_flags(0x08000000)
            .output();
    }
    #[cfg(not(target_os = "windows"))]
    {
        if let Some(ref mut child) = backend.process {
            let _ = child.kill();
            let _ = child.wait();
        }
    }

    // Wait for port to free up
    std::thread::sleep(std::time::Duration::from_secs(3));

    // Start new backend
    let python = find_python().ok_or("Python not found")?;
    let script = find_backend_script().ok_or("Backend script not found")?;

    // Log what we're doing
    let exe_dir = std::env::current_exe().ok().and_then(|p| p.parent().map(|d| d.to_path_buf()));
    if let Some(dir) = &exe_dir {
        let _ = std::fs::write(dir.join("switch_log.txt"), format!(
            "python: {}\nscript: {}\nproject: {}\nport: 7800\n", python, script, path
        ));
    }

    let mut cmd = Command::new(&python);
    cmd.args(&[&script, "--project", &path, "--port", "7800", "--no-ui"])
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    #[cfg(target_os = "windows")]
    cmd.creation_flags(0x08000000);

    match cmd.spawn() {
        Ok(child) => {
            backend.process = Some(child);
            backend.project_path = path.clone();
            Ok(format!("Switched to {}", path))
        }
        Err(e) => Err(format!("Failed to start backend: {}", e))
    }
}

#[tauri::command]
fn get_backend_project(state: tauri::State<'_, Mutex<BackendState>>) -> String {
    let backend = state.lock().unwrap();
    backend.project_path.clone()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let python = find_python();
            let script = find_backend_script();
            let project = find_project_path();

            let mut initial_project = String::new();
            let mut initial_process: Option<Child> = None;

            if let (Some(py), Some(sc), Some(proj)) = (&python, &script, &project) {
                initial_project = proj.clone();
                let mut cmd = Command::new(py);
                cmd.args(&[sc.as_str(), "--project", proj.as_str(), "--port", "7800", "--no-ui"])
                    .stdout(Stdio::null())
                    .stderr(Stdio::null());

                #[cfg(target_os = "windows")]
                cmd.creation_flags(0x08000000);

                if let Ok(child) = cmd.spawn() {
                    initial_process = Some(child);
                }
            }

            app.manage(Mutex::new(BackendState {
                process: initial_process,
                project_path: initial_project,
            }));

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![pick_folder, switch_project, get_backend_project])
        .run(tauri::generate_context!())
        .expect("error while running Agent-0");
}

fn find_python() -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        if let Ok(output) = Command::new("cmd")
            .args(&["/C", "where", "python"])
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .creation_flags(0x08000000)
            .output()
        {
            if let Ok(s) = String::from_utf8(output.stdout) {
                for line in s.lines() {
                    let p = line.trim();
                    if !p.is_empty() && !p.contains("WindowsApps") && std::path::Path::new(p).exists() {
                        return Some(p.to_string());
                    }
                }
            }
        }
    }
    None
}

fn find_backend_script() -> Option<String> {
    let exe_path = std::env::current_exe().ok()?;
    let exe_dir = exe_path.parent()?;
    let mut dir = exe_dir.to_path_buf();
    for _ in 0..6 {
        let candidate = dir.join("backend").join("main.py");
        if candidate.exists() {
            return Some(candidate.to_string_lossy().to_string());
        }
        dir = dir.parent()?.to_path_buf();
    }
    None
}

fn find_project_path() -> Option<String> {
    let exe_path = std::env::current_exe().ok()?;
    let exe_dir = exe_path.parent()?;
    let mut dir = exe_dir.to_path_buf();
    for _ in 0..6 {
        if dir.join("backend").exists() {
            return Some(dir.to_string_lossy().to_string());
        }
        dir = dir.parent()?.to_path_buf();
    }
    None
}
