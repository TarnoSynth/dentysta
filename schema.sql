CREATE DATABASE IF NOT EXISTS dental_clinic
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE dental_clinic;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS dentist_schedules;
DROP TABLE IF EXISTS dentist_treatments;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS dentists;
DROP TABLE IF EXISTS treatments;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  phone VARCHAR(20) NULL,
  role ENUM('patient', 'admin') NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE treatments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  description TEXT NULL,
  duration_minutes INT NOT NULL,
  price DECIMAL(10, 2) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE dentists (
  id INT AUTO_INCREMENT PRIMARY KEY,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE dentist_treatments (
  dentist_id INT NOT NULL,
  treatment_id INT NOT NULL,
  PRIMARY KEY (dentist_id, treatment_id),
  CONSTRAINT fk_dt_dentist FOREIGN KEY (dentist_id) REFERENCES dentists (id),
  CONSTRAINT fk_dt_treatment FOREIGN KEY (treatment_id) REFERENCES treatments (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE rooms (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE dentist_schedules (
  id INT AUTO_INCREMENT PRIMARY KEY,
  dentist_id INT NOT NULL,
  weekday TINYINT NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  CONSTRAINT fk_ds_dentist FOREIGN KEY (dentist_id) REFERENCES dentists (id),
  CONSTRAINT chk_weekday CHECK (weekday BETWEEN 0 AND 6),
  CONSTRAINT chk_schedule_order CHECK (start_time < end_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE appointments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_id INT NOT NULL,
  dentist_id INT NOT NULL,
  treatment_id INT NOT NULL,
  room_id INT NOT NULL,
  starts_at DATETIME NOT NULL,
  ends_at DATETIME NOT NULL,
  duration_minutes INT NOT NULL,
  price DECIMAL(10, 2) NULL,
  status ENUM('scheduled', 'completed', 'cancelled') NOT NULL DEFAULT 'scheduled',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ap_patient FOREIGN KEY (patient_id) REFERENCES users (id),
  CONSTRAINT fk_ap_dentist FOREIGN KEY (dentist_id) REFERENCES dentists (id),
  CONSTRAINT fk_ap_treatment FOREIGN KEY (treatment_id) REFERENCES treatments (id),
  CONSTRAINT fk_ap_room FOREIGN KEY (room_id) REFERENCES rooms (id),
  CONSTRAINT chk_appointment_order CHECK (starts_at < ends_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_appt_dentist_time ON appointments (dentist_id, starts_at, ends_at);
CREATE INDEX idx_appt_room_time ON appointments (room_id, starts_at, ends_at);
CREATE INDEX idx_appt_patient_time ON appointments (patient_id, starts_at);
