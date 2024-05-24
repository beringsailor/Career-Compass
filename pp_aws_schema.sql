-- MySQL dump 10.13  Distrib 8.0.36, for Win64 (x86_64)
--
-- Host: careercompass-1a.cpigyg0wwaz2.ap-northeast-1.rds.amazonaws.com    Database: pp_aws
-- ------------------------------------------------------
-- Server version	8.0.35

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ '';

--
-- Table structure for table `job`
--

DROP TABLE IF EXISTS `job`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `job` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `job_code` varchar(255) NOT NULL,
  `job_title` varchar(255) NOT NULL,
  `company_name` varchar(255) NOT NULL,
  `job_location` varchar(255) NOT NULL,
  `salary_period` varchar(255) DEFAULT NULL,
  `min_salary` bigint DEFAULT NULL,
  `max_salary` bigint DEFAULT NULL,
  `edu_level` varchar(255) DEFAULT NULL,
  `work_experience` varchar(255) DEFAULT NULL,
  `skills` varchar(255) DEFAULT NULL,
  `travel` varchar(255) DEFAULT NULL,
  `management` varchar(255) DEFAULT NULL,
  `remote` varchar(255) DEFAULT NULL,
  `job_source` varchar(255) NOT NULL,
  `create_date` timestamp NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `job_job_code_unique` (`job_code`)
) ENGINE=InnoDB AUTO_INCREMENT=103793 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `job_category`
--

DROP TABLE IF EXISTS `job_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `job_category` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `job_code` varchar(255) NOT NULL,
  `job_category` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_job_code` (`job_code`),
  KEY `job_code_category_idx` (`job_code`,`job_category`),
  CONSTRAINT `job_category_job_code_foreign` FOREIGN KEY (`job_code`) REFERENCES `job` (`job_code`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1266583 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `job_post_change`
--

DROP TABLE IF EXISTS `job_post_change`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `job_post_change` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `total_post` bigint NOT NULL,
  `ios` bigint NOT NULL,
  `android` bigint NOT NULL,
  `frontend` bigint NOT NULL,
  `backend` bigint NOT NULL,
  `fullstack` bigint NOT NULL,
  `data_analyst` bigint NOT NULL,
  `data_scientist` bigint NOT NULL,
  `data_engineer` bigint NOT NULL,
  `ai_engineer` bigint NOT NULL,
  `db_admin` bigint NOT NULL,
  `date` date NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_date` (`date`)
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_email_unique` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_bookmark`
--

DROP TABLE IF EXISTS `user_bookmark`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_bookmark` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint unsigned NOT NULL,
  `job_code` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_bookmark_user_id_foreign` (`user_id`),
  KEY `user_bookmark_job_code_foreign` (`job_code`),
  CONSTRAINT `user_bookmark_job_code_foreign` FOREIGN KEY (`job_code`) REFERENCES `job` (`job_code`) ON DELETE CASCADE,
  CONSTRAINT `user_bookmark_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=166 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-05-23 13:28:42
