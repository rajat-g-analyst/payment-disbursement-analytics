-- queries.sql
-- SQL queries used in the Payment Disbursement Analytics project (SQLite).
-- Table: payments (built from clean_payment_data.csv by clean_and_analyze.py)
-- Note: the data is synthetic (generated with Python), not real company data.

-- 1. Compare H2H and Manual payments
SELECT Payment_Method,
       COUNT(*) AS total_payments,
       ROUND(AVG(Approval_Days), 2) AS avg_approval_days,
       ROUND(100.0 * SUM(CASE WHEN Payment_Status = 'Processed' THEN 1 ELSE 0 END)
             / SUM(CASE WHEN Approval_Status = 'Approved' THEN 1 ELSE 0 END), 2) AS processed_pct_of_approved
FROM payments
GROUP BY Payment_Method;

-- 2. Exception rate (%) for each payment method
SELECT Payment_Method,
       COUNT(*) AS total_payments,
       SUM(CASE WHEN Exception_Type != 'None' THEN 1 ELSE 0 END) AS exceptions,
       ROUND(100.0 * SUM(CASE WHEN Exception_Type != 'None' THEN 1 ELSE 0 END)
             / COUNT(*), 2) AS exception_rate_pct
FROM payments
GROUP BY Payment_Method;

-- 3. Average approval time by region
SELECT Region,
       COUNT(*) AS total_payments,
       ROUND(AVG(Approval_Days), 2) AS avg_approval_days
FROM payments
GROUP BY Region
ORDER BY avg_approval_days DESC;

-- 4. Which exception types happen the most
SELECT Exception_Type, COUNT(*) AS total
FROM payments
WHERE Exception_Type != 'None'
GROUP BY Exception_Type
ORDER BY total DESC;

-- 5. Approval status vs payment status
SELECT Approval_Status, Payment_Status, COUNT(*) AS total
FROM payments
GROUP BY Approval_Status, Payment_Status
ORDER BY Approval_Status, total DESC;

-- 6. Slow approvals: approval took more than 3 days, by region
SELECT Region, COUNT(*) AS slow_approvals
FROM payments
WHERE Approval_Days > 3
GROUP BY Region
ORDER BY slow_approvals DESC;

-- 7. Monthly volume and change vs previous month (window function LAG)
SELECT month,
       total_payments,
       total_payments - LAG(total_payments) OVER (ORDER BY month) AS change_vs_prev_month
FROM (
    SELECT strftime('%Y-%m', Submission_Date) AS month,
           COUNT(*) AS total_payments
    FROM payments
    GROUP BY month
)
ORDER BY month;

-- 8. Top 3 requestors by total amount (INR) in each region (RANK window function)
SELECT Region, Requestor_ID, total_amount_inr, rank_in_region
FROM (
    SELECT Region,
           Requestor_ID,
           ROUND(SUM(Amount_INR), 2) AS total_amount_inr,
           RANK() OVER (PARTITION BY Region ORDER BY SUM(Amount_INR) DESC) AS rank_in_region
    FROM payments
    GROUP BY Region, Requestor_ID
)
WHERE rank_in_region <= 3
ORDER BY Region, rank_in_region;

-- 9. Top 5 beneficiaries by total requested amount (INR)
SELECT Beneficiary_Name,
       COUNT(*) AS total_requests,
       ROUND(SUM(Amount_INR), 2) AS total_requested_inr
FROM payments
GROUP BY Beneficiary_Name
ORDER BY total_requested_inr DESC
LIMIT 5;

-- 10. Exception type vs outcome (how each exception ends up)
SELECT Exception_Type,
       COUNT(*) AS total,
       SUM(CASE WHEN Approval_Status = 'Approved' THEN 1 ELSE 0 END) AS approved,
       SUM(CASE WHEN Approval_Status = 'On Hold' THEN 1 ELSE 0 END) AS on_hold,
       SUM(CASE WHEN Approval_Status = 'Rejected' THEN 1 ELSE 0 END) AS rejected,
       SUM(CASE WHEN Payment_Status = 'Processed' THEN 1 ELSE 0 END) AS processed
FROM payments
GROUP BY Exception_Type
ORDER BY total DESC;