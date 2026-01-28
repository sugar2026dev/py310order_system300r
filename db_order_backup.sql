-- MySQL dump 10.13  Distrib 8.0.45, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: db_order
-- ------------------------------------------------------
-- Server version	8.0.45

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

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',2,'add_permission'),(6,'Can change permission',2,'change_permission'),(7,'Can delete permission',2,'delete_permission'),(8,'Can view permission',2,'view_permission'),(9,'Can add group',3,'add_group'),(10,'Can change group',3,'change_group'),(11,'Can delete group',3,'delete_group'),(12,'Can view group',3,'view_group'),(13,'Can add content type',4,'add_contenttype'),(14,'Can change content type',4,'change_contenttype'),(15,'Can delete content type',4,'delete_contenttype'),(16,'Can view content type',4,'view_contenttype'),(17,'Can add session',5,'add_session'),(18,'Can change session',5,'change_session'),(19,'Can delete session',5,'delete_session'),(20,'Can view session',5,'view_session'),(21,'Can add 订单',6,'add_order'),(22,'Can change 订单',6,'change_order'),(23,'Can delete 订单',6,'delete_order'),(24,'Can view 订单',6,'view_order'),(25,'Can add 用户',7,'add_user'),(26,'Can change 用户',7,'change_user'),(27,'Can delete 用户',7,'delete_user'),(28,'Can view 用户',7,'view_user');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext COLLATE utf8mb4_unicode_ci,
  `object_repr` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_order_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_order_user_id` FOREIGN KEY (`user_id`) REFERENCES `order_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (1,'admin','logentry'),(3,'auth','group'),(2,'auth','permission'),(4,'contenttypes','contenttype'),(6,'order','order'),(7,'order','user'),(5,'sessions','session');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2026-01-24 14:11:04.094559'),(2,'contenttypes','0002_remove_content_type_name','2026-01-24 14:11:04.285305'),(3,'auth','0001_initial','2026-01-24 14:11:04.800326'),(4,'auth','0002_alter_permission_name_max_length','2026-01-24 14:11:04.935331'),(5,'auth','0003_alter_user_email_max_length','2026-01-24 14:11:04.946156'),(6,'auth','0004_alter_user_username_opts','2026-01-24 14:11:04.956230'),(7,'auth','0005_alter_user_last_login_null','2026-01-24 14:11:04.965598'),(8,'auth','0006_require_contenttypes_0002','2026-01-24 14:11:04.972015'),(9,'auth','0007_alter_validators_add_error_messages','2026-01-24 14:11:04.983851'),(10,'auth','0008_alter_user_username_max_length','2026-01-24 14:11:04.994176'),(11,'auth','0009_alter_user_last_name_max_length','2026-01-24 14:11:05.004588'),(12,'auth','0010_alter_group_name_max_length','2026-01-24 14:11:05.030852'),(13,'auth','0011_update_proxy_permissions','2026-01-24 14:11:05.043537'),(14,'auth','0012_alter_user_first_name_max_length','2026-01-24 14:11:05.055181'),(15,'order','0001_initial','2026-01-24 14:11:05.774950'),(16,'admin','0001_initial','2026-01-24 14:11:06.017436'),(17,'admin','0002_logentry_remove_auto_add','2026-01-24 14:11:06.030631'),(18,'admin','0003_logentry_add_action_flag_choices','2026-01-24 14:11:06.044026'),(19,'sessions','0001_initial','2026-01-24 14:11:06.114388');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `session_data` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
INSERT INTO `django_session` VALUES ('0d05laig3chb38na5yx4g0eyfnxg88ds','.eJxVjDsOwjAQBe_iGlmbrD9xSnrOYK0_IQZkIzuRQIi7Q6QU0L6ZNy9maV1mu7ZYbQpsZB07_G6O_DXmDYQL5XPhvuSlJsc3he-08VMJ8Xbc3b_ATG3-vr3SyiN12EfAYXIKgxZyMECDlJORDqMWZKSBzocJjNDeiV4hAOoelNiiLbaWSrbxcU_1yUZ4fwBRQj3D:1vkDAD:uTXj8wKTCRHG2_eem0Hs0IUvTlkSOCFp29X54PGPs7E','2026-02-09 03:21:17.102413'),('2muoui11hfwypnva7bvoubt3pj4vu92a','.eJxVjMsOwiAQRf-FtSFAy2O6dO83kKEMFjVgSptojP-uTbrQ7T3nnhfzuC6TXxvNPkc2sI4dfreA45XKBuIFy7nysZZlzoFvCt9p46ca6Xbc3b_AhG36vo1w0GOgzqnUayeDikk7CEKiVskmUsaJUXZKWKuBDCqJfdJRapCAYLdoo9ZyLZ4e9zw_2SCVACPE-wPU0D9f:1vkFeG:PrL-Bc77zaoru_ZZHt6Eup3ytLdrzAbbvvmF9ZUUi_o','2026-02-09 06:00:28.409858'),('4l3pnnse7ty5gp0i752ra8axo5qurpyv','.eJxVjDsOwjAQBe_iGlmbrD9xSnrOYK0_IQZkIzuRQIi7Q6QU0L6ZNy9maV1mu7ZYbQpsZB07_G6O_DXmDYQL5XPhvuSlJsc3he-08VMJ8Xbc3b_ATG3-vr3SyiN12EfAYXIKgxZyMECDlJORDqMWZKSBzocJjNDeiV4hAOoelNiiLbaWSrbxcU_1yUZ4fwBRQj3D:1vjqqd:CvEiFU49C_KGcD5xB-mSZwzkRnNnsUIAAWaRxbtAXxM','2026-02-08 03:31:35.141147'),('t2y43o4z17did45asaf80dmmg90ufbr7','.eJxVjssOwiAURP-FtSGXWwq0S_d-A-Fxa1EDTWkTjfHftaYL3c45M5kns25dRrtWmm2KrGfIDr-Zd-FKeQPx4vK58FDyMifPN4XvtPJTiXQ77u7fwOjq-GlL0aAYdGsMkMdBERBCKwx4qQaNAiVKpTsMoNH5hkQTodOBWm2kIvN9VanWVLKl-5TmB-vh9QYwbj2L:1vkDAi:zx-OjlHeMX_xxB2bGciIPvA9kZw0TmMFZvXqe0OPBRo','2026-02-09 03:21:48.987156');
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_info`
--

DROP TABLE IF EXISTS `order_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_info` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `order_code` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `upload_user` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ocr_result` longtext COLLATE utf8mb4_unicode_ci,
  `extracted_data` json NOT NULL,
  `img_filename` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `img_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_time` datetime(6) NOT NULL,
  `update_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_code` (`order_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_info`
--

LOCK TABLES `order_info` WRITE;
/*!40000 ALTER TABLE `order_info` DISABLE KEYS */;
/*!40000 ALTER TABLE `order_info` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_user`
--

DROP TABLE IF EXISTS `order_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `first_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_user`
--

LOCK TABLES `order_user` WRITE;
/*!40000 ALTER TABLE `order_user` DISABLE KEYS */;
INSERT INTO `order_user` VALUES (1,'pbkdf2_sha256$1000000$NvRR6GLcVSEFV6Wy3zhqMG$0GupozJxTCzrGDNLO3lgzJQuJjkFk+eLRp2aiARmEEc=','2026-01-26 03:21:17.094432',1,'cryokk','','',1,1,'2026-01-24 14:12:33.176016',''),(2,'pbkdf2_sha256$1000000$qy8urm4ZD8JYRqRJ5rYUay$rOb3g8SY8/Fpy7IPaCi0DboffvBp71K+14mriiUySCY=','2026-01-26 03:35:11.109383',0,'test1','','',0,1,'2026-01-26 03:21:42.888511',''),(3,'pbkdf2_sha256$1000000$E6O44LrjYzs1j8xGlUQY0B$sxqgHb4dH824jKWwxgycITZoNhK6PCdq/LyK5jHycXw=','2026-01-26 06:00:28.402376',0,'sugar','','',0,1,'2026-01-26 06:00:23.023311','');
/*!40000 ALTER TABLE `order_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_user_groups`
--

DROP TABLE IF EXISTS `order_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_user_groups_user_id_group_id_7ddb183c_uniq` (`user_id`,`group_id`),
  KEY `order_user_groups_group_id_89683b18_fk_auth_group_id` (`group_id`),
  CONSTRAINT `order_user_groups_group_id_89683b18_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `order_user_groups_user_id_afb7d617_fk_order_user_id` FOREIGN KEY (`user_id`) REFERENCES `order_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_user_groups`
--

LOCK TABLES `order_user_groups` WRITE;
/*!40000 ALTER TABLE `order_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `order_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_user_user_permissions`
--

DROP TABLE IF EXISTS `order_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_user_user_permissions_user_id_permission_id_08f24d83_uniq` (`user_id`,`permission_id`),
  KEY `order_user_user_perm_permission_id_77e6aa47_fk_auth_perm` (`permission_id`),
  CONSTRAINT `order_user_user_perm_permission_id_77e6aa47_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `order_user_user_permissions_user_id_59e6240c_fk_order_user_id` FOREIGN KEY (`user_id`) REFERENCES `order_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_user_user_permissions`
--

LOCK TABLES `order_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `order_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `order_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-26 22:35:28
