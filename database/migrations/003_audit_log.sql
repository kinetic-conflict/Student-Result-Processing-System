-- Migration 003: append-only record of who changed what.
-- Never stores passwords or hashes. `username` is copied so the entry still
-- reads correctly after an account is removed.

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    username VARCHAR(50) NULL,
    action VARCHAR(50) NOT NULL,
    entity VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50) NULL,
    detail VARCHAR(500) NULL,
    ip_address VARCHAR(45) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_created (created_at),
    INDEX idx_audit_user (user_id),
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;
