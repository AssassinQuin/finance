-- MySQL dump 10.13  Distrib 9.6.0, for Linux (aarch64)
--
-- Host: localhost    Database: fcli
-- ------------------------------------------------------
-- Server version	9.6.0

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

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ '58dc6924-12e8-11f1-b834-da5586f8c46e:1-217';

--
-- Current Database: `fcli`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `fcli` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `fcli`;

--
-- Table structure for table `central_bank_schedules`
--

DROP TABLE IF EXISTS `central_bank_schedules`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `central_bank_schedules` (
  `id` int NOT NULL AUTO_INCREMENT,
  `country_code` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `country_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `release_day` tinyint DEFAULT NULL,
  `release_frequency` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'monthly',
  `last_release_date` date DEFAULT NULL,
  `next_expected_date` date DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `country_code` (`country_code`)
) ENGINE=InnoDB AUTO_INCREMENT=81 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `exchange_rates`
--

DROP TABLE IF EXISTS `exchange_rates`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exchange_rates` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `from_currency` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '源货币',
  `to_currency` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '目标货币',
  `rate` decimal(18,8) NOT NULL COMMENT '汇率',
  `rate_date` date NOT NULL COMMENT '汇率日期',
  `data_source` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '数据来源',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pair_date` (`from_currency`,`to_currency`,`rate_date`),
  KEY `idx_rate_date` (`rate_date`),
  KEY `idx_from_currency` (`from_currency`),
  KEY `idx_to_currency` (`to_currency`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='汇率数据';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `fetch_logs`
--

DROP TABLE IF EXISTS `fetch_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fetch_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `data_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `records_count` int DEFAULT '0',
  `duration_ms` int DEFAULT '0',
  `error_message` text COLLATE utf8mb4_unicode_ci,
  `timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_data_type_timestamp` (`data_type`,`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gold_reserves`
--

DROP TABLE IF EXISTS `gold_reserves`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `gold_reserves` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `country_code` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'å›½å®¶ä»£ç ',
  `country_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'å›½å®¶åç§°',
  `amount_tonnes` decimal(15,2) NOT NULL DEFAULT '0.00' COMMENT 'é»„é‡‘å‚¨å¤‡(å¨)',
  `gold_share_pct` decimal(8,4) DEFAULT NULL COMMENT '占外储比例(%)',
  `gold_value_usd_m` decimal(15,2) DEFAULT NULL COMMENT '价值(百万美元)',
  `percent_of_reserves` decimal(8,4) DEFAULT NULL COMMENT 'å å¤–å‚¨æ¯”ä¾‹(%)',
  `report_date` date NOT NULL COMMENT 'æŠ¥å‘Šæ—¥æœŸ',
  `data_source` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fetch_time` datetime DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_country_date` (`country_code`,`report_date`),
  KEY `idx_report_date` (`report_date`),
  KEY `idx_country_code` (`country_code`)
) ENGINE=InnoDB AUTO_INCREMENT=12626 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='é»„é‡‘å‚¨å¤‡åŽ†å²æ•°æ®';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gpr_history`
--

DROP TABLE IF EXISTS `gpr_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `gpr_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `period` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `gpr_value` decimal(10,2) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `period` (`period`),
  KEY `idx_period` (`period`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `migrations`
--

DROP TABLE IF EXISTS `migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `migrations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `version` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `quotes`
--

DROP TABLE IF EXISTS `quotes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `quotes` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `symbol` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '代码',
  `name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '名称',
  `type` enum('stock','fund','index','bond','other') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '类型',
  `exchange` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '交易所',
  `price` decimal(18,4) DEFAULT NULL COMMENT '价格',
  `change_pct` decimal(8,4) DEFAULT NULL COMMENT '涨跌幅(%)',
  `volume` bigint DEFAULT NULL COMMENT '成交量',
  `turnover` decimal(20,2) DEFAULT NULL COMMENT '成交额',
  `market_cap` decimal(20,2) DEFAULT NULL COMMENT '市值',
  `pe_ratio` decimal(10,4) DEFAULT NULL COMMENT '市盈率',
  `pb_ratio` decimal(10,4) DEFAULT NULL COMMENT '市净率',
  `dividend_yield` decimal(8,4) DEFAULT NULL COMMENT '股息率(%)',
  `quote_date` date NOT NULL COMMENT '行情日期',
  `quote_time` datetime DEFAULT NULL COMMENT '行情时间',
  `data_source` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '数据来源',
  `extra_data` json DEFAULT NULL COMMENT '扩展数据',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_symbol_date` (`symbol`,`quote_date`),
  KEY `idx_quote_date` (`quote_date`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_type` (`type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='行情数据';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `watchlist_assets`
--

DROP TABLE IF EXISTS `watchlist_assets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `watchlist_assets` (
  `id` int NOT NULL AUTO_INCREMENT,
  `code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户输入代码',
  `api_code` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'API查询代码',
  `name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '资产名称',
  `market` enum('CN','US','HK','GLOBAL') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'CN' COMMENT '市场',
  `type` enum('INDEX','FUND','STOCK','BOND','OTHER') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'OTHER' COMMENT '类型',
  `extra` json DEFAULT NULL COMMENT '扩展信息',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否有效',
  `added_at` datetime DEFAULT NULL COMMENT '添加时间',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  KEY `idx_market` (`market`),
  KEY `idx_type` (`type`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='自选资产';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping events for database 'fcli'
--

--
-- Dumping routines for database 'fcli'
--
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-02-27  8:49:10
