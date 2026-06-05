SELECT 
    DATE(`进出时间`) AS `日期`, 
    COUNT(*) AS `日入馆人次`
FROM `门禁日志`
GROUP BY DATE(`进出时间`)
ORDER BY `日期`;


SELECT 
    `学院`, 
    SUM(`总借阅量`) AS `学院总借阅册数`
FROM `读者`
GROUP BY `学院`
ORDER BY `学院总借阅册数` DESC
LIMIT 10;

-- 查询不同读者类型的人均入馆次数与人均借阅量
SELECT 
    `读者类型`,
    COUNT(*) AS `群体总人数`,
    -- 考虑到基数可能较大，使用 ROUND 保留一位小数计算人均指标
    ROUND(AVG(`入馆次数`), 1) AS `人均入馆次数`,
    ROUND(AVG(`总借阅量`), 1) AS `人均借阅量`
FROM `读者`
WHERE `读者类型` IS NOT NULL AND `读者类型` != '未知'
GROUP BY `读者类型`
HAVING `群体总人数` > 50  -- 过滤掉个别测试数据，保证统计有效性
ORDER BY `群体总人数` DESC;

-- 查询不同读者类型的 24 小时入馆行为特征
SELECT 
    r.`读者类型`,
    HOUR(g.`进出时间`) AS `24小时时段`,
    COUNT(g.`日志编号`) AS `入馆总人次`
FROM `门禁日志` g
JOIN `读者` r ON g.`学号` = r.`学号`
-- 过滤掉凌晨闭馆期间可能存在的系统测试脏数据
WHERE HOUR(g.`进出时间`) BETWEEN 6 AND 23 
  AND r.`读者类型` IS NOT NULL 
  AND r.`读者类型` != '未知'
GROUP BY r.`读者类型`, HOUR(g.`进出时间`)
ORDER BY r.`读者类型`, `24小时时段`;

CREATE INDEX idx_borrow_cno ON `借阅记录` (`图书条码`);
SELECT  
    bk.`图书类型`, 
    COUNT(DISTINCT bk.`图书条码`) AS `馆藏总册数`, 
    COUNT(DISTINCT br.`图书条码`) AS `曾被借阅册数`, 
    ROUND(COUNT(DISTINCT br.`图书条码`) / COUNT(DISTINCT bk.`图书条码`) * 100, 2) AS `流通率(%)` 
FROM `图书` bk 
LEFT JOIN `借阅记录` br ON bk.`图书条码` = br.`图书条码` 
GROUP BY bk.`图书类型` 
HAVING `馆藏总册数` > 100 
ORDER BY `流通率(%)` DESC;

SELECT `学号`, `入馆次数`, `总借阅量`
FROM `读者`
WHERE `入馆次数` > 100 
  AND `学号` NOT IN (
      SELECT `学号`
      FROM `读者`
      WHERE `总借阅量` >= 3
  );

SELECT 
    r.`学号`, 
    r.`学院`, 
    r.`总借阅量`, 
    ROUND(avg_dept.`平均借阅量`, 2) AS `本院平均借阅量`
FROM `读者` r,
     -- 派生表 avg_dept
     (SELECT `学院`, AVG(`总借阅量`) AS `平均借阅量`
      FROM `读者`
      GROUP BY `学院`) AS avg_dept
WHERE r.`学院` = avg_dept.`学院` 
  AND r.`总借阅量` > avg_dept.`平均借阅量` * 2 -- 借阅量超过平均值两倍才算卷王
ORDER BY (r.`总借阅量` - avg_dept.`平均借阅量`) DESC
LIMIT 50;

-- 查询去过了“信息工程分馆”所有阅览室的读者学号与学院
SELECT r.`学号`, r.`学院`
FROM `读者` r
WHERE NOT EXISTS (
    -- 第一层否定：不存在这样一个“信息工程分馆”的阅览室
    SELECT *
    FROM `阅览室` rm
    WHERE rm.`名称` LIKE '信息工程分馆%'
      AND NOT EXISTS (
          -- 第二层否定：该读者没有在这个阅览室留下过座位日志
          SELECT *
          FROM `座位日志` s
          WHERE s.`学号` = r.`学号` 
            AND s.`阅览室编号` = rm.`编号`
      )
);

WITH Target_Month_Visits AS (
    -- 优化1：利用 WHERE 切片，将 900万 数据降维到 20万 左右的单月数据
    -- 优化2：使用 GROUP BY 替代 DISTINCT，减轻排序负担
    SELECT `学号`, DATE(`进出时间`) AS `访问日期`
    FROM `门禁日志`
    WHERE `进出时间` >= '2018-06-01' AND `进出时间` < '2018-07-01'
    GROUP BY `学号`, DATE(`进出时间`)
),
Ranked_Visits AS (
    -- 此时参与窗口函数计算的数据量已极小，毫秒级出结果
    SELECT `学号`, `访问日期`,
           ROW_NUMBER() OVER(PARTITION BY `学号` ORDER BY `访问日期`) AS rn
    FROM Target_Month_Visits
),
Streak_Groups AS (
    SELECT `学号`, `访问日期`,
           DATE_SUB(`访问日期`, INTERVAL rn DAY) AS `基准日期`
    FROM Ranked_Visits
)
SELECT 
    `学号`, 
    MIN(`访问日期`) AS `连续起始日`, 
    MAX(`访问日期`) AS `连续结束日`, 
    COUNT(*) AS `连续打卡天数`
FROM Streak_Groups
GROUP BY `学号`, `基准日期`
HAVING COUNT(*) >= 7
ORDER BY `连续打卡天数` DESC;

WITH Event_Stream AS (
    -- 提取 2018 年 6 月的“入座”事件
    SELECT `阅览室编号`, `开始时间` AS `event_time`, 1 AS `change_val`
    FROM `座位日志`
    WHERE `开始时间` >= '2018-06-01' AND `开始时间` < '2018-07-01'
      AND `结束时间` IS NOT NULL
    
    UNION ALL
    
    -- 提取 2018 年 6 月的“离座”事件
    SELECT `阅览室编号`, `结束时间` AS `event_time`, -1 AS `change_val`
    FROM `座位日志`
    WHERE `结束时间` >= '2018-06-01' AND `结束时间` < '2018-07-01'
      AND `开始时间` IS NOT NULL
),
Running_Total AS (
    -- 在切片后的几万条事件流中计算瞬时人数，性能极佳
    SELECT `阅览室编号`, `event_time`,
           SUM(`change_val`) OVER(PARTITION BY `阅览室编号` ORDER BY `event_time` ASC) AS `current_occupancy`
    FROM Event_Stream
)
SELECT 
    `阅览室编号`, 
    `event_time` AS `达到峰值的精确时间`, 
    `current_occupancy` AS `最高并发人数`
FROM (
    SELECT `阅览室编号`, `event_time`, `current_occupancy`,
           RANK() OVER(PARTITION BY `阅览室编号` ORDER BY `current_occupancy` DESC) AS rnk
    FROM Running_Total
) t
WHERE rnk = 1;


-- 第2步：在图书表建立复合覆盖索引（将分组字段和连接字段打包，彻底消灭回表）
CREATE INDEX idx_book_type_cno ON `图书` (`图书类型`, `图书条码`);
-- 第3步：确保借阅记录表的连接字段有单独索引（加速 LEFT JOIN）
CREATE INDEX idx_borrow_cno ON `借阅记录` (`图书条码`);
SELECT  
    bk.`图书类型`, 
    COUNT(DISTINCT bk.`图书条码`) AS `馆藏总册数`, 
    COUNT(DISTINCT br.`图书条码`) AS `曾被借阅册数`, 
    ROUND(COUNT(DISTINCT br.`图书条码`) / COUNT(DISTINCT bk.`图书条码`) * 100, 2) AS `流通率(%)` 
FROM `图书` bk 
LEFT JOIN `借阅记录` br ON bk.`图书条码` = br.`图书条码` 
GROUP BY bk.`图书类型` 
HAVING `馆藏总册数` > 100 
ORDER BY `流通率(%)` DESC;