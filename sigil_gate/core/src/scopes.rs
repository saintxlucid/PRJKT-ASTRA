use serde::{Deserialize, Serialize};
use regex::Regex;
use globset::{Glob, GlobMatcher};
use std::path::Path;
use crate::errors::{Result, SigilError};

/// Scope kind (operation type)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ScopeKind {
    /// File system read
    FsRead,
    /// File system write (create/delete/modify)
    FsWrite,
    /// Network egress
    NetEgress,
    /// Process spawn
    ProcSpawn,
}

/// Parsed scope rule
#[derive(Debug, Clone)]
pub struct ScopeRule {
    pub kind: ScopeKind,
    pub pattern: String,
    pub glob_matcher: Option<GlobMatcher>,
    pub port: Option<u16>,
}

impl ScopeRule {
    /// Parse scope string (e.g., "fs.write:C:/Projects/**")
    pub fn parse(scope: &str) -> Result<Self> {
        let (kind_str, value) = scope
            .split_once(':')
            .ok_or_else(|| SigilError::ScopeDenied(format!("Invalid scope format: {}", scope)))?;

        let kind = match kind_str {
            "fs.read" => ScopeKind::FsRead,
            "fs.write" => ScopeKind::FsWrite,
            "net.egress" => ScopeKind::NetEgress,
            "proc.spawn" => ScopeKind::ProcSpawn,
            _ => return Err(SigilError::ScopeDenied(format!("Unknown scope kind: {}", kind_str))),
        };

        match kind {
            ScopeKind::FsRead | ScopeKind::FsWrite => {
                let glob = Glob::new(value)
                    .map_err(|e| SigilError::ScopeDenied(format!("Invalid glob pattern: {}", e)))?;
                Ok(Self {
                    kind,
                    pattern: value.to_string(),
                    glob_matcher: Some(glob.compile_matcher()),
                    port: None,
                })
            }
            ScopeKind::NetEgress => {
                let mut parts = value.split(':');
                let host = parts.next().unwrap_or("*").to_string();
                let port = parts.next().and_then(|p| p.parse().ok());
                Ok(Self {
                    kind,
                    pattern: host,
                    glob_matcher: None,
                    port,
                })
            }
            ScopeKind::ProcSpawn => Ok(Self {
                kind,
                pattern: value.to_string(),
                glob_matcher: None,
                port: None,
            }),
        }
    }

    /// Check if path matches this scope
    pub fn matches_path(&self, path: &Path) -> bool {
        if let Some(matcher) = &self.glob_matcher {
            matcher.is_match(path)
        } else {
            false
        }
    }

    /// Check if host:port matches this scope
    pub fn matches_host(&self, host: &str, port: u16) -> bool {
        if self.kind != ScopeKind::NetEgress {
            return false;
        }

        // Check port
        if let Some(scope_port) = self.port {
            if scope_port != port {
                return false;
            }
        }

        // Check host pattern
        if self.pattern == "*" {
            return true;
        }

        // Wildcard domain matching (*.example.com)
        if self.pattern.starts_with("*.") {
            let domain_suffix = &self.pattern[2..];
            return host.ends_with(domain_suffix) || host == domain_suffix;
        }

        // Exact match
        host == self.pattern
    }

    /// Check if command matches this scope
    pub fn matches_command(&self, cmd: &str) -> bool {
        if self.kind != ScopeKind::ProcSpawn {
            return false;
        }
        cmd.contains(&self.pattern)
    }
}

/// Scope validator
pub struct Scope {
    rules: Vec<ScopeRule>,
}

impl Scope {
    /// Create from list of scope strings
    pub fn from_strings(scopes: &[String]) -> Result<Self> {
        let rules = scopes
            .iter()
            .map(|s| ScopeRule::parse(s))
            .collect::<Result<Vec<_>>>()?;
        Ok(Self { rules })
    }

    /// Check if file read is allowed
    pub fn allows_fs_read(&self, path: &Path) -> bool {
        self.rules
            .iter()
            .any(|r| r.kind == ScopeKind::FsRead && r.matches_path(path))
    }

    /// Check if file write is allowed
    pub fn allows_fs_write(&self, path: &Path) -> bool {
        self.rules
            .iter()
            .any(|r| r.kind == ScopeKind::FsWrite && r.matches_path(path))
    }

    /// Check if network egress is allowed
    pub fn allows_net_egress(&self, host: &str, port: u16) -> bool {
        self.rules
            .iter()
            .any(|r| r.kind == ScopeKind::NetEgress && r.matches_host(host, port))
    }

    /// Check if process spawn is allowed
    pub fn allows_proc_spawn(&self, cmd: &str) -> bool {
        self.rules
            .iter()
            .any(|r| r.kind == ScopeKind::ProcSpawn && r.matches_command(cmd))
    }

    /// Get all rules of a specific kind
    pub fn rules_of_kind(&self, kind: ScopeKind) -> Vec<&ScopeRule> {
        self.rules.iter().filter(|r| r.kind == kind).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_fs_scope_parsing() {
        let rule = ScopeRule::parse("fs.write:C:/Projects/**").unwrap();
        assert_eq!(rule.kind, ScopeKind::FsWrite);
        assert_eq!(rule.pattern, "C:/Projects/**");
    }

    #[test]
    fn test_fs_scope_matching() {
        let rule = ScopeRule::parse("fs.write:C:/Projects/**").unwrap();
        assert!(rule.matches_path(&PathBuf::from("C:/Projects/test.txt")));
        assert!(rule.matches_path(&PathBuf::from("C:/Projects/sub/test.txt")));
        assert!(!rule.matches_path(&PathBuf::from("C:/Other/test.txt")));
    }

    #[test]
    fn test_net_scope_parsing() {
        let rule = ScopeRule::parse("net.egress:*.openai.com:443").unwrap();
        assert_eq!(rule.kind, ScopeKind::NetEgress);
        assert_eq!(rule.pattern, "*.openai.com");
        assert_eq!(rule.port, Some(443));
    }

    #[test]
    fn test_net_scope_matching() {
        let rule = ScopeRule::parse("net.egress:*.openai.com:443").unwrap();
        assert!(rule.matches_host("api.openai.com", 443));
        assert!(rule.matches_host("chat.openai.com", 443));
        assert!(!rule.matches_host("api.openai.com", 80));
        assert!(!rule.matches_host("google.com", 443));
    }

    #[test]
    fn test_wildcard_all() {
        let rule = ScopeRule::parse("net.egress:*:443").unwrap();
        assert!(rule.matches_host("anything.com", 443));
        assert!(!rule.matches_host("anything.com", 80));
    }

    #[test]
    fn test_scope_validator() {
        let scopes = vec![
            "fs.write:C:/Projects/**".to_string(),
            "net.egress:*.openai.com:443".to_string(),
        ];
        let scope = Scope::from_strings(&scopes).unwrap();

        assert!(scope.allows_fs_write(&PathBuf::from("C:/Projects/test.txt")));
        assert!(!scope.allows_fs_write(&PathBuf::from("C:/Other/test.txt")));
        assert!(scope.allows_net_egress("api.openai.com", 443));
        assert!(!scope.allows_net_egress("google.com", 443));
    }
}
