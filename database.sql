-- ============================================================
-- 智慧校园图书借阅信息管理系统 V2.0 —— 融合版数据库 DDL
-- 融合来源：
--   1. 基于Python的校园图书借阅信息管理软件（业务模块）
--   2. SmartLib 智慧图书馆系统（空间管理 + AI 问答）
-- 数据库：MySQL 8.0+
-- 编码：utf8mb4
-- ============================================================

CREATE DATABASE IF NOT EXISTS `smart_library_v2`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `smart_library_v2`;

-- ------------------------------------------------------------
-- 1. 分类字典表（categories）
-- 来源：校园图书借阅信息管理软件
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `categories` (
    `code`          VARCHAR(10)     NOT NULL    COMMENT '中图法分类编码',
    `name`          VARCHAR(100)    NOT NULL    COMMENT '分类名称',
    `level`         INT             NOT NULL    COMMENT '分类层级（1=一级类，2=二级类）',
    `parent_code`   VARCHAR(10)     NULL        COMMENT '父级分类编码',
    `created_at`    DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`code`),
    INDEX `idx_parent` (`parent_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='图书分类字典表（中图法）';

-- ------------------------------------------------------------
-- 2. 图书主表（books）
-- 融合：校园图书版（ISBN主键 + 库存管理） + SmartLib版（条码、索书号、语言）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `books` (
    `isbn`              VARCHAR(13)     NOT NULL    COMMENT 'ISBN-13（国际标准书号）',
    `barcode`           VARCHAR(50)     NOT NULL    COMMENT '图书馆内部条码（SmartLib）',
    `title`             VARCHAR(255)    NOT NULL    COMMENT '书名',
    `authors`           VARCHAR(500)    NOT NULL    COMMENT '作者列表',
    `publisher`         VARCHAR(255)    NOT NULL    COMMENT '出版社',
    `publish_year`      INT             NULL        COMMENT '出版年份',
    `category_code`     VARCHAR(10)     NOT NULL    COMMENT '分类编码',
    `call_no`           VARCHAR(100)    NULL        COMMENT '索书号（中图法排架号，SmartLib）',
    `language`          VARCHAR(20)     DEFAULT '中文' COMMENT '图书语言',
    `doc_type`          VARCHAR(50)     DEFAULT '普通图书' COMMENT '文献类型',
    `total_copies`      INT             NOT NULL    DEFAULT 1 COMMENT '馆藏总册数',
    `available_copies`  INT             NOT NULL    DEFAULT 1 COMMENT '当前可借册数',
    `location`          VARCHAR(50)     NOT NULL    COMMENT '馆藏位置（如：3F-A区-08-B层）',
    `status`            VARCHAR(10)     NOT NULL    DEFAULT '在库' COMMENT '在库/借出/下架/遗失/编目中',
    `created_at`        DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '录入时间',
    `updated_at`        DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    PRIMARY KEY (`isbn`),
    UNIQUE KEY `uk_barcode` (`barcode`),
    INDEX `idx_title` (`title`),
    INDEX `idx_category` (`category_code`),
    INDEX `idx_status` (`status`),
    FULLTEXT INDEX `ft_title_authors` (`title`, `authors`) COMMENT 'MySQL全文检索',
    CONSTRAINT `chk_isbn_length` CHECK (LENGTH(`isbn`) = 13),
    CONSTRAINT `chk_copies_positive` CHECK (`total_copies` >= 0 AND `available_copies` >= 0),
    CONSTRAINT `chk_copies_consistency` CHECK (`total_copies` >= `available_copies`),
    CONSTRAINT `fk_book_category` FOREIGN KEY (`category_code`) REFERENCES `categories`(`code`)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='图书主信息表（融合版）';

-- ------------------------------------------------------------
-- 3. 图书库存实时表（book_inventory）
-- 来源：校园图书版，独立维护便于并发事务
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `book_inventory` (
    `isbn`      VARCHAR(13) NOT NULL    COMMENT 'ISBN',
    `stock`     INT         NOT NULL    DEFAULT 0 COMMENT '实时库存（与 available_copies 逻辑一致）',
    `updated_at` DATETIME   DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`isbn`),
    CONSTRAINT `chk_stock_positive` CHECK (`stock` >= 0),
    CONSTRAINT `fk_inv_book` FOREIGN KEY (`isbn`) REFERENCES `books`(`isbn`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='图书库存实时表';

-- ------------------------------------------------------------
-- 4. 用户/读者主表（users）
-- 融合：校园图书版（安全体系） + SmartLib版（入学年份、读者类型）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
    `id`                INT             AUTO_INCREMENT  COMMENT '内部主键',
    `uid`               VARCHAR(20)     NOT NULL        COMMENT '学工号（唯一标识）',
    `real_name`         VARCHAR(50)     NOT NULL        COMMENT '真实姓名',
    `gender`            VARCHAR(10)     NULL            COMMENT '性别',
    `enroll_year`       VARCHAR(4)      NULL            COMMENT '入学年份（SmartLib）',
    `department`        VARCHAR(100)    NOT NULL        COMMENT '院系/部门',
    `role`              VARCHAR(20)     NOT NULL        DEFAULT 'student' COMMENT 'student/teacher/libadmin/sysadmin',
    `reader_type`       VARCHAR(50)     NULL            COMMENT '读者类型细分（SmartLib）',
    `id_type`           VARCHAR(20)     NOT NULL        DEFAULT '身份证' COMMENT '证件类型',
    `id_number_enc`     VARCHAR(255)    NOT NULL        COMMENT 'AES-256加密证件号',
    `phone_enc`         VARCHAR(255)    NOT NULL        COMMENT 'AES-256加密手机号',
    `email`             VARCHAR(100)    NULL            COMMENT '邮箱',
    `avatar_path`       VARCHAR(255)    NULL            COMMENT '头像文件路径',
    `password_hash`     VARCHAR(255)    NULL            COMMENT 'PBKDF2密码哈希',
    `register_time`     DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    `review_status`     VARCHAR(20)     DEFAULT 'pending' COMMENT 'pending/approved/rejected',
    `user_status`       VARCHAR(20)     DEFAULT 'pending_review' COMMENT '状态机字段',
    `max_borrow_count`  INT             DEFAULT 5 COMMENT '最大可借数量',
    `max_borrow_days`   INT             DEFAULT 30 COMMENT '最大借阅天数',
    `last_login`        DATETIME        NULL        COMMENT '最后登录时间',
    `failed_login_count` INT            DEFAULT 0 COMMENT '连续登录失败次数',
    `lock_expires`      DATETIME        NULL        COMMENT '账户锁定过期时间',
    `access_count`      INT             DEFAULT 0   COMMENT '累计入馆次数（预计算，SmartLib融合）',
    `borrow_count`      INT             DEFAULT 0   COMMENT '累计借阅册数（预计算，SmartLib融合）',
    `created_at`        DATETIME        DEFAULT CURRENT_TIMESTAMP,
    `updated_at`        DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_uid` (`uid`),
    INDEX `idx_role` (`role`),
    INDEX `idx_department` (`department`),
    INDEX `idx_status` (`user_status`),
    INDEX `idx_reader_type` (`reader_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户/读者主表（融合版）';

-- ------------------------------------------------------------
-- 5. 用户联系信息扩展表（user_profiles）
-- 来源：校园图书版，便于通知模块独立查询
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_profiles` (
    `user_id`           INT             NOT NULL    COMMENT '关联 users.id',
    `wechat_openid`     VARCHAR(50)     NULL        COMMENT '微信OpenID',
    `notify_preference` VARCHAR(50)     DEFAULT 'email,wechat' COMMENT '通知偏好顺序',
    `contact_status`    VARCHAR(10)     DEFAULT 'active' COMMENT 'active/inactive',
    `updated_at`        DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`user_id`),
    CONSTRAINT `fk_profile_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户联系信息扩展表';

-- ------------------------------------------------------------
-- 6. 借阅记录主表（borrow_records）
-- 融合：校园图书版（事务字段 + 逾期） + SmartLib版（续借次数）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `borrow_records` (
    `borrow_id`         VARCHAR(32)     NOT NULL    COMMENT '借阅流水号（UUID或业务号）',
    `user_id`           INT             NOT NULL    COMMENT '借阅人（users.id）',
    `isbn`              VARCHAR(13)     NOT NULL    COMMENT '图书ISBN',
    `borrow_time`       DATETIME        NOT NULL    COMMENT '借阅时间',
    `due_time`          DATETIME        NOT NULL    COMMENT '应还时间',
    `return_time`       DATETIME        NULL        COMMENT '实际归还时间',
    `operator_id`       INT             NULL        COMMENT '操作员（users.id）',
    `status`            VARCHAR(20)     NOT NULL    DEFAULT 'borrowed' COMMENT 'borrowed/returned/overdue/renewed/lost',
    `overdue_days`      INT             DEFAULT 0 COMMENT '逾期天数',
    `renew_count`       INT             DEFAULT 0 COMMENT '续借次数（SmartLib）',
    `is_deleted`        TINYINT(1)      DEFAULT 0 COMMENT '逻辑删除标记',
    `created_at`        DATETIME        DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`borrow_id`),
    INDEX `idx_br_user` (`user_id`),
    INDEX `idx_br_isbn` (`isbn`),
    INDEX `idx_br_status` (`status`),
    INDEX `idx_br_return` (`return_time`),
    INDEX `idx_br_borrow_time` (`borrow_time`),
    CONSTRAINT `fk_br_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`),
    CONSTRAINT `fk_br_book` FOREIGN KEY (`isbn`) REFERENCES `books`(`isbn`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='借阅记录主表（融合版）';

-- ------------------------------------------------------------
-- 7. 阅览室表（reading_rooms）
-- 来源：SmartLib（空间管理）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `reading_rooms` (
    `room_no`       VARCHAR(20)     NOT NULL    COMMENT '阅览室编号',
    `room_name`     VARCHAR(100)    NOT NULL    COMMENT '阅览室名称',
    `location`      VARCHAR(100)    NULL        COMMENT '物理位置',
    `capacity`      INT             NULL        COMMENT '座位容量',
    `status`        VARCHAR(20)     DEFAULT 'open' COMMENT 'open/closed/maintenance',
    PRIMARY KEY (`room_no`),
    INDEX `idx_room_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='阅览室信息表（SmartLib融合）';

-- ------------------------------------------------------------
-- 8. 门禁日志表（access_logs）
-- 来源：SmartLib（空间管理）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `access_logs` (
    `log_id`        BIGINT          AUTO_INCREMENT  COMMENT '日志ID',
    `user_id`       INT             NOT NULL        COMMENT '用户ID',
    `visit_time`    DATETIME        NOT NULL        COMMENT '进出时间',
    `location`      VARCHAR(50)     NULL            COMMENT '门禁地点',
    `access_type`   VARCHAR(10)     DEFAULT 'in'    COMMENT 'in/out',
    PRIMARY KEY (`log_id`),
    INDEX `idx_access_user` (`user_id`),
    INDEX `idx_access_time` (`visit_time`),
    CONSTRAINT `fk_access_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='门禁进出日志表（SmartLib融合）';

-- ------------------------------------------------------------
-- 9. 座位日志表（seat_logs）
-- 来源：SmartLib（空间管理）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `seat_logs` (
    `log_id`        BIGINT          AUTO_INCREMENT  COMMENT '日志ID',
    `user_id`       INT             NOT NULL        COMMENT '用户ID',
    `room_no`       VARCHAR(20)     NOT NULL        COMMENT '阅览室编号',
    `seat_no`       VARCHAR(20)     NOT NULL        COMMENT '座位号',
    `start_time`    DATETIME        NOT NULL        COMMENT '占座开始时间',
    `end_time`      DATETIME        NULL            COMMENT '离座结束时间',
    PRIMARY KEY (`log_id`),
    INDEX `idx_seat_user` (`user_id`),
    INDEX `idx_seat_room` (`room_no`),
    INDEX `idx_seat_time` (`start_time`),
    CONSTRAINT `fk_seat_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`),
    CONSTRAINT `fk_seat_room` FOREIGN KEY (`room_no`) REFERENCES `reading_rooms`(`room_no`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='座位预约/使用日志表（SmartLib融合）';

-- ------------------------------------------------------------
-- 10. 权限规则表（permission_rules）
-- 来源：校园图书版（RBAC + ABAC）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `permission_rules` (
    `id`            INT             AUTO_INCREMENT  COMMENT '规则ID',
    `role`          VARCHAR(20)     NOT NULL        COMMENT '角色',
    `resource`      VARCHAR(100)    NOT NULL        COMMENT '资源标识（book/borrow/user/room）',
    `action`        VARCHAR(50)     NOT NULL        COMMENT '操作（create/read/update/delete）',
    `condition`     VARCHAR(500)    NULL            COMMENT 'ABAC动态规则表达式（JSON或DSL）',
    `created_at`    DATETIME        DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_perm_role_res_act` (`role`, `resource`, `action`),
    INDEX `idx_perm_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='权限规则表（RBAC+ABAC）';

-- ------------------------------------------------------------
-- 11. 操作审计日志表（audit_logs）
-- 来源：校园图书版
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `audit_logs` (
    `id`            BIGINT          AUTO_INCREMENT  COMMENT '日志ID',
    `user_id`       INT             NOT NULL        COMMENT '被操作对象用户ID',
    `action`        VARCHAR(50)     NOT NULL        COMMENT '操作类型',
    `old_value`     VARCHAR(255)    NULL            COMMENT '变更前值',
    `new_value`     VARCHAR(255)    NULL            COMMENT '变更后值',
    `operator_id`   INT             NOT NULL        COMMENT '执行操作的管理员ID',
    `ip_address`    VARCHAR(45)     NULL            COMMENT '操作者IP',
    `user_agent`    VARCHAR(255)    NULL            COMMENT '操作者UA',
    `timestamp`     DATETIME        DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_audit_user` (`user_id`),
    INDEX `idx_audit_time` (`timestamp`),
    INDEX `idx_audit_action` (`action`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='操作审计日志表';

-- ------------------------------------------------------------
-- 12. 系统参数配置表（system_config）
-- 来源：校园图书版
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `system_config` (
    `config_key`    VARCHAR(50)     NOT NULL    COMMENT '参数名',
    `config_value`  VARCHAR(255)    NOT NULL    COMMENT '参数值',
    `description`   VARCHAR(255)    NULL        COMMENT '参数说明',
    `updated_at`    DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='系统参数配置表';

-- 初始化系统参数
INSERT INTO `system_config` (`config_key`, `config_value`, `description`) VALUES
('max_borrow_days', '30', '默认最大借阅天数'),
('max_books_student', '5', '学生最大可借数量'),
('max_books_teacher', '10', '教师最大可借数量'),
('default_due_days', '30', '默认借期天数'),
('notification_cooldown_hours', '24', '同类型通知冷却时间（幂等控制）'),
('permission_cache_ttl', '1800', '权限缓存过期时间（秒）')
ON DUPLICATE KEY UPDATE `config_value` = VALUES(`config_value`);

-- ------------------------------------------------------------
-- 13. 通知消息日志表（message_logs）
-- 来源：校园图书版
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `message_logs` (
    `log_id`        BIGINT          AUTO_INCREMENT  COMMENT '日志ID',
    `user_id`       INT             NOT NULL        COMMENT '接收用户ID',
    `borrow_id`     VARCHAR(32)     NULL            COMMENT '关联借阅记录',
    `channel`       VARCHAR(20)     NOT NULL        COMMENT 'email/wechat/in_app/sms',
    `template_code` VARCHAR(30)     NOT NULL        COMMENT '模板编码',
    `content`       TEXT            NOT NULL        COMMENT '消息正文',
    `send_time`     DATETIME        DEFAULT CURRENT_TIMESTAMP,
    `status`        VARCHAR(10)     DEFAULT 'pending' COMMENT 'pending/sent/failed',
    `error_msg`     TEXT            NULL            COMMENT '失败原因',
    `notify_type`   VARCHAR(20)     NOT NULL        COMMENT 'due_soon/overdue_dayN/renew_reminder',
    `notify_level`  INT             DEFAULT 1,
    PRIMARY KEY (`log_id`),
    INDEX `idx_msg_user` (`user_id`),
    INDEX `idx_msg_borrow` (`borrow_id`),
    INDEX `idx_msg_type_time` (`notify_type`, `send_time`),
    INDEX `idx_msg_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='通知消息日志表';

-- ------------------------------------------------------------
-- 14. 视图：学院借阅统计（融合 SmartLib 大屏需求）
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW `v_department_borrow_stats` AS
SELECT
    u.`department`      AS `学院`,
    COUNT(*)            AS `总借阅次数`,
    COUNT(DISTINCT br.`user_id`) AS `活跃读者数`,
    SUM(CASE WHEN br.`status` = 'overdue' THEN 1 ELSE 0 END) AS `逾期次数`,
    ROUND(SUM(CASE WHEN br.`status` = 'overdue' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS `逾期率`
FROM `borrow_records` br
JOIN `users` u ON br.`user_id` = u.`id`
WHERE br.`is_deleted` = 0
GROUP BY u.`department`
ORDER BY `总借阅次数` DESC;

-- ------------------------------------------------------------
-- 15. 视图：月度借阅趋势（融合 SmartLib 大屏需求）
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW `v_monthly_borrow_trend` AS
SELECT
    DATE_FORMAT(`borrow_time`, '%Y-%m') AS `月份`,
    COUNT(*)                            AS `借阅次数`,
    COUNT(DISTINCT `user_id`)           AS `借阅人数`,
    COUNT(DISTINCT `isbn`)              AS `借阅种类`
FROM `borrow_records`
WHERE `is_deleted` = 0
GROUP BY DATE_FORMAT(`borrow_time`, '%Y-%m')
ORDER BY `月份`;

-- ------------------------------------------------------------
-- 16. 读者时段汇总表（user_hour_stats）
-- 来源：SmartLib 大屏优化（避免每次扫描 16M+ 门禁日志）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_hour_stats` (
    `reader_type`   VARCHAR(50)     NOT NULL    COMMENT '读者类型',
    `hour`          INT             NOT NULL    COMMENT '小时（0-23）',
    `access_count`  INT             DEFAULT 0   COMMENT '该时段入馆人次',
    PRIMARY KEY (`reader_type`, `hour`),
    INDEX `idx_uhs_hour` (`hour`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='读者入馆时段汇总表（预计算，用于 24h 热力图）';

-- ============================================================
-- 数据库初始化完成
-- ============================================================
