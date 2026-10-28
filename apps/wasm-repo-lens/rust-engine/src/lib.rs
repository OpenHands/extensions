use std::collections::HashMap;
use std::slice;
use std::str;
use std::sync::Mutex;

static RESULT: Mutex<Vec<u8>> = Mutex::new(Vec::new());

#[derive(Clone)]
struct FileRecord {
    path: String,
    bytes: u64,
    language: String,
}

#[derive(Default)]
struct Aggregate {
    files: u64,
    bytes: u64,
}

#[derive(Default)]
struct Snapshot {
    branch: Option<String>,
    files: Vec<FileRecord>,
    content: HashMap<String, String>,
    churn: HashMap<String, u64>,
    history_entries: u64,
    truncated: bool,
}

#[derive(Default)]
struct Reference {
    source: String,
    count: u64,
}

#[no_mangle]
pub extern "C" fn alloc(size: usize) -> *mut u8 {
    let mut buffer = Vec::<u8>::with_capacity(size);
    let pointer = buffer.as_mut_ptr();
    std::mem::forget(buffer);
    pointer
}

#[no_mangle]
pub unsafe extern "C" fn dealloc(pointer: *mut u8, size: usize) {
    if size > 0 && !pointer.is_null() {
        drop(Vec::from_raw_parts(pointer, 0, size));
    }
}

#[no_mangle]
pub unsafe extern "C" fn analyze(pointer: *const u8, size: usize) -> i32 {
    let input = if size == 0 {
        ""
    } else if pointer.is_null() {
        return store_error("The snapshot input pointer was null.");
    } else {
        match str::from_utf8(slice::from_raw_parts(pointer, size)) {
            Ok(value) => value,
            Err(_) => return store_error("The repository snapshot was not valid UTF-8."),
        }
    };

    match parse_snapshot(input) {
        Ok(snapshot) => match build_analysis(snapshot) {
            Ok(output) => {
                *RESULT.lock().expect("result lock") = output.into_bytes();
                0
            }
            Err(message) => store_error(&message),
        },
        Err(message) => store_error(&message),
    }
}

#[no_mangle]
pub extern "C" fn result_ptr() -> *const u8 {
    RESULT.lock().expect("result lock").as_ptr()
}

#[no_mangle]
pub extern "C" fn result_len() -> usize {
    RESULT.lock().expect("result lock").len()
}

fn store_error(message: &str) -> i32 {
    *RESULT.lock().expect("result lock") = message.as_bytes().to_vec();
    1
}

fn parse_snapshot(input: &str) -> Result<Snapshot, String> {
    let mut snapshot = Snapshot::default();
    let mut saw_version = false;
    for line in input.lines() {
        let mut fields = line.split('\t');
        match fields.next().unwrap_or("") {
            "V" => {
                if fields.next() != Some("1") {
                    return Err("The Agent Server returned an unsupported snapshot version.".into());
                }
                saw_version = true;
            }
            "B" => {
                let value = decode_text(fields.next().unwrap_or(""))?;
                snapshot.branch = if value.is_empty() { None } else { Some(value) };
            }
            "F" => {
                let path = decode_text(fields.next().unwrap_or(""))?;
                let bytes = fields.next().unwrap_or("0").parse::<u64>().unwrap_or(0);
                if !valid_relative_path(&path) {
                    return Err("The snapshot contained an invalid relative file path.".into());
                }
                snapshot.files.push(FileRecord {
                    language: classify_language(&path).to_string(),
                    path,
                    bytes,
                });
            }
            "C" => {
                let path = decode_text(fields.next().unwrap_or(""))?;
                let content = decode_text_lossy(fields.next().unwrap_or(""))?;
                if valid_relative_path(&path) {
                    snapshot.content.insert(path, content);
                }
            }
            "H" => {
                let path = decode_text(fields.next().unwrap_or(""))?;
                if valid_relative_path(&path) {
                    *snapshot.churn.entry(path).or_insert(0) += 1;
                    snapshot.history_entries += 1;
                }
            }
            "T" => snapshot.truncated = true,
            "" => {}
            _ => return Err("The Agent Server returned an incomplete snapshot record. The command response may have been truncated.".into()),
        }
    }
    if !saw_version {
        return Err("The Agent Server response was not a Repo Lens snapshot.".into());
    }
    Ok(snapshot)
}

fn valid_relative_path(path: &str) -> bool {
    !path.is_empty()
        && !path.starts_with('/')
        && !path.contains('\0')
        && !path.split('/').any(|part| part == "..")
}

fn decode_text(value: &str) -> Result<String, String> {
    String::from_utf8(decode_base64(value)?).map_err(|_| "A snapshot path was not valid UTF-8.".into())
}

fn decode_text_lossy(value: &str) -> Result<String, String> {
    Ok(String::from_utf8_lossy(&decode_base64(value)?).into_owned())
}

fn decode_base64(value: &str) -> Result<Vec<u8>, String> {
    let mut output = Vec::with_capacity(value.len() * 3 / 4);
    let mut block = [0u8; 4];
    let mut used = 0;
    for byte in value.bytes().filter(|byte| !byte.is_ascii_whitespace()) {
        if byte == b'=' {
            break;
        }
        block[used] = match byte {
            b'A'..=b'Z' => byte - b'A',
            b'a'..=b'z' => byte - b'a' + 26,
            b'0'..=b'9' => byte - b'0' + 52,
            b'+' => 62,
            b'/' => 63,
            _ => return Err("The snapshot contained invalid base64 data.".into()),
        };
        used += 1;
        if used == 4 {
            output.push((block[0] << 2) | (block[1] >> 4));
            output.push((block[1] << 4) | (block[2] >> 2));
            output.push((block[2] << 6) | block[3]);
            used = 0;
        }
    }
    if used == 2 {
        output.push((block[0] << 2) | (block[1] >> 4));
    } else if used == 3 {
        output.push((block[0] << 2) | (block[1] >> 4));
        output.push((block[1] << 4) | (block[2] >> 2));
    } else if used == 1 {
        return Err("The snapshot contained truncated base64 data.".into());
    }
    Ok(output)
}

fn classify_language(path: &str) -> &'static str {
    let name = path.rsplit('/').next().unwrap_or(path).to_ascii_lowercase();
    if name == "dockerfile" { return "Dockerfile"; }
    if name == "makefile" || name == "gnumakefile" { return "Makefile"; }
    if name == "cargo.toml" { return "TOML"; }
    if name == "go.mod" || name == "go.sum" { return "Go Modules"; }
    if name == "package.json" || name.ends_with("lock.json") { return "JSON"; }
    let extension = name.rsplit_once('.').map(|(_, ext)| ext).unwrap_or("");
    match extension {
        "ts" | "tsx" => "TypeScript",
        "js" | "jsx" | "mjs" | "cjs" => "JavaScript",
        "py" | "pyi" => "Python",
        "rs" => "Rust",
        "go" => "Go",
        "java" => "Java",
        "kt" | "kts" => "Kotlin",
        "c" | "h" => "C",
        "cc" | "cpp" | "cxx" | "hpp" => "C++",
        "cs" => "C#",
        "rb" => "Ruby",
        "php" => "PHP",
        "swift" => "Swift",
        "vue" => "Vue",
        "svelte" => "Svelte",
        "html" | "htm" => "HTML",
        "css" | "scss" | "sass" | "less" => "CSS",
        "md" | "mdx" => "Markdown",
        "json" | "jsonc" => "JSON",
        "toml" => "TOML",
        "yaml" | "yml" => "YAML",
        "sh" | "bash" | "zsh" => "Shell",
        "sql" => "SQL",
        "wasm" => "WebAssembly",
        "svg" => "SVG",
        _ => "Other",
    }
}

fn add_reference(map: &mut HashMap<String, Reference>, name: &str, source: &str) {
    let clean = name.trim_matches(|ch: char| ch == '"' || ch == '\'' || ch == ',' || ch == ';').trim();
    if clean.is_empty() || clean.starts_with('.') || clean.starts_with('/') || clean.len() > 160 { return; }
    let entry = map.entry(clean.to_string()).or_insert_with(|| Reference { source: source.to_string(), count: 0 });
    entry.count += 1;
}

fn collect_package_json(content: &str, source: &str, dependencies: &mut HashMap<String, Reference>) {
    for section in ["dependencies", "devDependencies", "peerDependencies"] {
        let marker = format!("\"{}\"", section);
        let Some(start) = content.find(&marker) else { continue };
        let rest = &content[start + marker.len()..];
        let Some(open) = rest.find('{') else { continue };
        let object = &rest[open + 1..];
        let end = object.find('}').unwrap_or(object.len());
        for line in object[..end].lines() {
            let trimmed = line.trim();
            if let Some(after_quote) = trimmed.strip_prefix('"') {
                if let Some(close) = after_quote.find('"') {
                    add_reference(dependencies, &after_quote[..close], source);
                }
            }
        }
    }
}

fn collect_manifest(path: &str, content: &str, dependencies: &mut HashMap<String, Reference>) {
    let name = path.rsplit('/').next().unwrap_or(path);
    if name == "package.json" {
        collect_package_json(content, path, dependencies);
    } else if name == "requirements.txt" {
        for line in content.lines() {
            let package = line.split(|ch: char| matches!(ch, '=' | '<' | '>' | '~' | '!' | '[' | ';' | '#')).next().unwrap_or("");
            add_reference(dependencies, package, path);
        }
    } else if name == "Cargo.toml" {
        let mut in_dependencies = false;
        for line in content.lines() {
            let trimmed = line.trim();
            if trimmed.starts_with('[') {
                in_dependencies = trimmed.contains("dependencies");
            } else if in_dependencies {
                if let Some((package, _)) = trimmed.split_once('=') {
                    add_reference(dependencies, package, path);
                }
            }
        }
    } else if name == "go.mod" {
        for line in content.lines() {
            let trimmed = line.trim();
            if trimmed.starts_with("require ") {
                add_reference(dependencies, trimmed.split_whitespace().nth(1).unwrap_or(""), path);
            } else if !trimmed.starts_with(['/', ')']) && trimmed.split_whitespace().nth(1).is_some_and(|value| value.starts_with('v')) {
                add_reference(dependencies, trimmed.split_whitespace().next().unwrap_or(""), path);
            }
        }
    } else if name == "pyproject.toml" {
        let mut in_dependencies = false;
        for line in content.lines() {
            let trimmed = line.trim();
            if trimmed.starts_with('[') { in_dependencies = trimmed.contains("dependencies"); }
            if in_dependencies {
                if let Some((package, _)) = trimmed.split_once('=') {
                    add_reference(dependencies, package, path);
                } else if let Some(quoted) = trimmed.strip_prefix('"').or_else(|| trimmed.strip_prefix('\'')) {
                    let package = quoted.split(|ch: char| matches!(ch, '"' | '\'' | '=' | '<' | '>' | '~' | '[')).next().unwrap_or("");
                    add_reference(dependencies, package, path);
                }
            }
        }
    }
}

fn quoted_after(value: &str, marker: &str) -> Option<String> {
    let start = value.find(marker)? + marker.len();
    let rest = value[start..].trim_start();
    let quote = rest.chars().next()?;
    if quote != '"' && quote != '\'' { return None; }
    Some(rest[1..].split(quote).next()?.to_string())
}

fn package_root(name: &str) -> String {
    if name.starts_with('@') {
        name.split('/').take(2).collect::<Vec<_>>().join("/")
    } else {
        name.split(['/', '.']).next().unwrap_or(name).to_string()
    }
}

fn collect_imports(path: &str, content: &str, imports: &mut HashMap<String, Reference>) {
    for line in content.lines().take(500) {
        let trimmed = line.trim();
        let mut found: Option<String> = None;
        if trimmed.starts_with("import ") {
            found = quoted_after(trimmed, " from ").or_else(|| quoted_after(trimmed, "import "));
            if found.is_none() {
                found = trimmed.split_whitespace().nth(1).map(|value| value.trim_end_matches(',').to_string());
            }
        } else if trimmed.starts_with("from ") {
            found = trimmed.split_whitespace().nth(1).map(str::to_string);
        } else if let Some(value) = quoted_after(trimmed, "require(") {
            found = Some(value);
        } else if trimmed.starts_with("use ") {
            found = trimmed.split_whitespace().nth(1).map(|value| value.trim_end_matches(';').to_string());
        } else if trimmed.starts_with("#include") {
            found = trimmed.split(['<', '>', '"']).nth(1).map(str::to_string);
        }
        if let Some(value) = found {
            let root = package_root(value.trim());
            if !matches!(root.as_str(), "crate" | "self" | "super" | "std") {
                add_reference(imports, &root, path);
            }
        }
    }
}

fn escape_json(value: &str) -> String {
    let mut result = String::with_capacity(value.len() + 2);
    for ch in value.chars() {
        match ch {
            '"' => result.push_str("\\\""),
            '\\' => result.push_str("\\\\"),
            '\n' => result.push_str("\\n"),
            '\r' => result.push_str("\\r"),
            '\t' => result.push_str("\\t"),
            ch if ch < ' ' => result.push_str(&format!("\\u{:04x}", ch as u32)),
            ch => result.push(ch),
        }
    }
    result
}

fn ranked_json(map: HashMap<String, Aggregate>, total_bytes: u64) -> String {
    let mut values: Vec<_> = map.into_iter().collect();
    values.sort_by(|a, b| b.1.bytes.cmp(&a.1.bytes).then_with(|| a.0.cmp(&b.0)));
    values.into_iter().map(|(name, item)| {
        let percent = if total_bytes == 0 { 0.0 } else { item.bytes as f64 * 100.0 / total_bytes as f64 };
        format!("{{\"name\":\"{}\",\"files\":{},\"bytes\":{},\"percent\":{:.1}}}", escape_json(&name), item.files, item.bytes, percent)
    }).collect::<Vec<_>>().join(",")
}

fn references_json(map: HashMap<String, Reference>, kind: &str) -> String {
    let mut values: Vec<_> = map.into_iter().collect();
    values.sort_by(|a, b| b.1.count.cmp(&a.1.count).then_with(|| a.0.cmp(&b.0)));
    values.truncate(30);
    values.into_iter().map(|(name, item)| format!(
        "{{\"name\":\"{}\",\"source\":\"{}\",\"kind\":\"{}\",\"references\":{}}}",
        escape_json(&name), escape_json(&item.source), kind, item.count
    )).collect::<Vec<_>>().join(",")
}

fn build_analysis(snapshot: Snapshot) -> Result<String, String> {
    let mut languages: HashMap<String, Aggregate> = HashMap::new();
    let mut directories: HashMap<String, Aggregate> = HashMap::new();
    let mut dependencies = HashMap::new();
    let mut imports = HashMap::new();
    let total_bytes: u64 = snapshot.files.iter().map(|file| file.bytes).sum();

    for file in &snapshot.files {
        let language = languages.entry(file.language.clone()).or_default();
        language.files += 1;
        language.bytes += file.bytes;
        let directory_name = file.path.split_once('/').map(|(first, _)| first).unwrap_or("(root)");
        let directory = directories.entry(directory_name.to_string()).or_default();
        directory.files += 1;
        directory.bytes += file.bytes;
    }

    for (path, content) in &snapshot.content {
        collect_manifest(path, content, &mut dependencies);
        collect_imports(path, content, &mut imports);
    }

    let mut large_files = snapshot.files.clone();
    large_files.sort_by(|a, b| b.bytes.cmp(&a.bytes).then_with(|| a.path.cmp(&b.path)));
    large_files.truncate(12);
    let large_json = large_files.iter().map(|file| format!(
        "{{\"path\":\"{}\",\"bytes\":{},\"language\":\"{}\"}}",
        escape_json(&file.path), file.bytes, escape_json(&file.language)
    )).collect::<Vec<_>>().join(",");

    let size_lookup: HashMap<&str, (&str, u64)> = snapshot.files.iter()
        .map(|file| (file.path.as_str(), (file.language.as_str(), file.bytes)))
        .collect();
    let mut churn: Vec<_> = snapshot.churn.into_iter().collect();
    churn.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
    churn.truncate(12);
    let churn_json = churn.iter().map(|(path, changes)| {
        let (language, bytes) = size_lookup.get(path.as_str()).copied().unwrap_or(("Other", 0));
        format!("{{\"path\":\"{}\",\"bytes\":{},\"changes\":{},\"language\":\"{}\"}}", escape_json(path), bytes, changes, escape_json(language))
    }).collect::<Vec<_>>().join(",");

    let branch = snapshot.branch.map(|value| format!("\"{}\"", escape_json(&value))).unwrap_or_else(|| "null".into());
    Ok(format!(
        "{{\"branch\":{},\"files\":{},\"bytes\":{},\"sourceSamples\":{},\"historyEntries\":{},\"truncated\":{},\"languages\":[{}],\"directories\":[{}],\"largeFiles\":[{}],\"churnHotspots\":[{}],\"dependencies\":[{}],\"imports\":[{}]}}",
        branch,
        snapshot.files.len(),
        total_bytes,
        snapshot.content.len(),
        snapshot.history_entries,
        snapshot.truncated,
        ranked_json(languages, total_bytes),
        ranked_json(directories, total_bytes),
        large_json,
        churn_json,
        references_json(dependencies, "dependency"),
        references_json(imports, "import"),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn analyzes_protocol_records() {
        let snapshot = parse_snapshot("V\t1\nB\tbWFpbg==\nF\tc3JjL2xpYi5ycw==\t120\nC\tc3JjL2xpYi5ycw==\tdXNlIHNlcmRlOwo=\nH\tc3JjL2xpYi5ycw==\nT\tcontent-bytes\n").unwrap();
        let output = build_analysis(snapshot).unwrap();
        assert!(output.contains("\"branch\":\"main\""));
        assert!(output.contains("\"name\":\"Rust\""));
        assert!(output.contains("\"path\":\"src/lib.rs\""));
        assert!(output.contains("\"name\":\"serde\""));
        assert!(output.contains("\"truncated\":true"));
    }

    #[test]
    fn rejects_parent_traversal() {
        assert!(parse_snapshot("V\t1\nF\tLi4vc2VjcmV0\t1\n").is_err());
    }
}
