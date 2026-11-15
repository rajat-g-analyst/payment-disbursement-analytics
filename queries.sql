-- queries.sql
-- SQL queries used in the Payment Disbursement Analytics project (SQLite).
-- Table: payments (built from clean_payment_data.csv by clean_and_analyze.py)
-- Note: the data is synthetic (generated with Python), not real company data.

-- 1. How many approved payments each method got processed
SELECT Payment_Method,
       COUNT(*) AS total_payments,
       SUM(CASE WHEN Approval_Status = 'Approved' THEN 1 ELSE 0 END) AS approved,
       SUM(CASE WHEN Payment_Status = 'Processed' THEN 1 ELSE 0 END) AS processed,
       ROUND(100.0 * SUM(CASE WHEN Payment_Status = 'Processed' THEN 1 ELSE 0 END)
             / SUM(CASE WHEN Approval_Status = 'Approved' THEN 1 ELSE 0 END), 2) AS processed_pct_of_approved
FROM payments
GROUP BY Payment_Method;

-- 2. % of payments with an exception, per method
SELECT Payment_Method,
       COUNT(*) AS total_payments,
       SUM(CASE WHEN Exception_Type != 'None' THEN 1 ELSE 0 END) AS exceptions,
       ROUND(100.0 * SUM(CASE WHEN Exception_Type != 'None' THEN 1 ELSE 0 END)
             / COUNT(*), 2) AS exception_rate_pct
FROM payments
GROUP BY Payment_Method;

-- 3. Average days to approve, per region (approved payments only)
SELECT Region,
       COUNT(*) AS approved_payments,
       ROUND(AVG(Approval_Days), 2) AS avg_approval_days
FROM payments
WHERE Approval_Status = 'Approved'
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

-- 6. Approvals that took more than 3 days, per region
SELECT Region,
       COUNT(*) AS approved_payments,
       SUM(CASE WHEN Approval_Days > 3 THEN 1 ELSE 0 END) AS slow_approvals,
       ROUND(100.0 * SUM(CASE WHEN Approval_Days > 3 THEN 1 ELSE 0 END)
             / COUNT(*), 2) AS slow_approval_pct
FROM payments
WHERE Approval_Status = 'Approved'
GROUP BY Region
ORDER BY slow_approval_pct DESC;

-- 7. Payments per month, and change from the previous month (LAG)
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

-- 8. Top 3 requestors in each region (RANK)
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

-- 9. Top 5 beneficiaries by total amount (INR)
SELECT Beneficiary_Name,
       Currency,
       COUNT(*) AS total_payments,
       ROUND(SUM(Amount_INR), 2) AS total_amount_inr
FROM payments
GROUP BY Beneficiary_Name, Currency
ORDER BY total_amount_inr DESC
LIMIT 5;

-- 10. What happens to payments with and without an exception
SELECT CASE WHEN Exception_Type = 'None' THEN 'No exception' ELSE 'Exception' END AS exception_flag,
       COUNT(*) AS total_payments,
       ROUND(100.0 * SUM(CASE WHEN Approval_Status = 'Approved' THEN 1 ELSE 0 END) / COUNT(*), 2) AS approved_pct,
       ROUND(100.0 * SUM(CASE WHEN Approval_Status = 'On Hold' THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_hold_pct,
       ROUND(100.0 * SUM(CASE WHEN Approval_Status = 'Rejected' THEN 1 ELSE 0 END) / COUNT(*), 2) AS rejected_pct
FROM payments
GROUP BY exception_flag;