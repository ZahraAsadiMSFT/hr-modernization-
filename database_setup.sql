-- Sample Database Setup for HR Document Generation System
-- This script creates tables, sample data, and stored procedures for testing
-- 
-- Prerequisites:
-- 1. Create an Azure SQL Database or SQL Server instance
-- 2. Update the database name below if different from 'hr0025'
-- 3. Run this script as a user with CREATE TABLE permissions

-- Ensure we are in the right DB (change if your DB name is different)
USE hr0025;
GO

/* Clean up if you partially created objects earlier */
IF OBJECT_ID('dbo.Deductions','U') IS NOT NULL DROP TABLE dbo.Deductions;
IF OBJECT_ID('dbo.Payruns','U')    IS NOT NULL DROP TABLE dbo.Payruns;
IF OBJECT_ID('dbo.TaxSummary','U') IS NOT NULL DROP TABLE dbo.TaxSummary;
IF OBJECT_ID('dbo.Employees','U')  IS NOT NULL DROP TABLE dbo.Employees;
GO

/* 1) Create Tables */

-- Employee master data
CREATE TABLE dbo.Employees (
    EmployeeId INT PRIMARY KEY,
    EmployeeNumber NVARCHAR(20) UNIQUE NOT NULL,
    FullName NVARCHAR(200) NOT NULL,
    SIN NVARCHAR(20) NULL  -- Social Insurance Number (Canadian)
);
GO

-- Payroll periods and calculations
CREATE TABLE dbo.Payruns (
    PayrunId INT IDENTITY PRIMARY KEY,
    EmployeeId INT NOT NULL REFERENCES dbo.Employees(EmployeeId),
    PeriodStart DATE NOT NULL,
    PeriodEnd DATE NOT NULL,
    GrossAmount DECIMAL(18,2) NOT NULL,
    NetAmount DECIMAL(18,2) NOT NULL
);
GO

-- Tax and benefit deductions
CREATE TABLE dbo.Deductions (
    DeductionId INT IDENTITY PRIMARY KEY,
    PayrunId INT NOT NULL REFERENCES dbo.Payruns(PayrunId),
    CPP DECIMAL(18,2) NULL,  -- Canada Pension Plan
    EI DECIMAL(18,2) NULL    -- Employment Insurance
);
GO

-- Annual tax summary data for T4/T4A forms
CREATE TABLE dbo.TaxSummary (
    TaxSummaryId INT IDENTITY PRIMARY KEY,
    EmployeeId INT NOT NULL REFERENCES dbo.Employees(EmployeeId),
    [Year] INT NOT NULL,
    FormType NVARCHAR(10) NOT NULL,  -- 'T4', 'T4A', etc.
    Box14 DECIMAL(18,2) NULL,        -- Employment income
    Box22 DECIMAL(18,2) NULL         -- Income tax deducted
);
GO

/* 2) Insert Sample Data */

-- Sample employees (includes duplicate names for testing disambiguation)
INSERT INTO dbo.Employees (EmployeeId, EmployeeNumber, FullName, SIN)
VALUES 
(1, '102938', N'Alex Martin',  '123-456-789'),
(2, '445566', N'Alex Martin',  '123-456-790'),  -- Duplicate name for testing
(3, '556677', N'Jordan Lee',   '987-654-321'),
(4, '778899', N'Sofia Alvarez','222-333-444');
GO

-- Sample payruns (bi-monthly samples across years/employees)
INSERT INTO dbo.Payruns (EmployeeId, PeriodStart, PeriodEnd, GrossAmount, NetAmount)
VALUES
-- Alex Martin (102938) - 2022
(1,'2022-01-01','2022-01-15',4200.00,3200.00),
(1,'2022-01-16','2022-01-31',4200.00,3190.00),
(1,'2022-03-01','2022-03-15',4200.00,3200.00),
-- Alex Martin (102938) - 2023
(1,'2023-02-01','2023-02-15',4300.00,3280.00),
(1,'2023-02-16','2023-02-28',4300.00,3275.00),
-- Alex Martin (445566) - 2022 (different Alex for disambiguation testing)
(2,'2022-01-01','2022-01-15',3800.00,2900.00),
(2,'2022-01-16','2022-01-31',3800.00,2895.00),
-- Jordan Lee (2023)
(3,'2023-01-01','2023-01-15',3900.00,3000.00),
(3,'2023-01-16','2023-01-31',3900.00,2995.00),
(3,'2023-02-01','2023-02-15',3950.00,3050.00),
-- Sofia Alvarez (2024)
(4,'2024-01-01','2024-01-15',4500.00,3400.00),
(4,'2024-01-16','2024-01-31',4500.00,3395.00);
GO

-- Sample deductions for each payrun
INSERT INTO dbo.Deductions (PayrunId, CPP, EI)
VALUES
(1,150.00,35.00),   -- Alex 102938 Jan 1-15
(2,150.00,35.00),   -- Alex 102938 Jan 16-31
(3,152.00,36.00),   -- Alex 102938 Mar 1-15
(4,155.00,36.00),   -- Alex 102938 Feb 1-15 (2023)
(5,156.00,37.00),   -- Alex 102938 Feb 16-28 (2023)
(6,135.00,30.00),   -- Alex 445566 Jan 1-15
(7,135.00,30.00),   -- Alex 445566 Jan 16-31
(8,140.00,32.00),   -- Jordan Jan 1-15
(9,141.00,32.00),   -- Jordan Jan 16-31
(10,142.00,33.00),  -- Jordan Feb 1-15
(11,160.00,38.00),  -- Sofia Jan 1-15
(12,160.00,38.00);  -- Sofia Jan 16-31
GO

-- Sample tax summaries for T4 and T4A forms
INSERT INTO dbo.TaxSummary (EmployeeId, [Year], FormType, Box14, Box22)
VALUES
-- Alex Martin (102938)
(1, 2022, 'T4', 50400.00, 8000.00),
(1, 2023, 'T4', 51600.00, 8200.00),
-- Alex Martin (445566) 
(2, 2022, 'T4', 45600.00, 7200.00),
-- Jordan Lee
(3, 2023, 'T4', 46800.00, 7600.00),
-- Sofia Alvarez
(4, 2024, 'T4', 54000.00, 8600.00),
(4, 2024, 'T4A',  5000.00,  500.00);  -- Additional T4A form
GO

/* 3) Create Required Stored Procedures */

-- Retrieve payslip data for a date range
CREATE OR ALTER PROCEDURE dbo.sp_GetPaystubForRange
  @EmployeeNumber NVARCHAR(20),
  @From DATE,
  @To DATE
AS
BEGIN
  SET NOCOUNT ON;
  SELECT e.FullName,
         e.EmployeeNumber,
         p.PeriodStart,
         p.PeriodEnd,
         p.GrossAmount,
         p.NetAmount,
         d.CPP,
         d.EI
  FROM dbo.Employees e
  JOIN dbo.Payruns p ON p.EmployeeId = e.EmployeeId
  LEFT JOIN dbo.Deductions d ON d.PayrunId = p.PayrunId
  WHERE e.EmployeeNumber = @EmployeeNumber
    AND p.PeriodStart >= @From
    AND p.PeriodEnd   <= @To
  ORDER BY p.PeriodStart;
END
GO

-- Retrieve tax form data (T4/T4A)
CREATE OR ALTER PROCEDURE dbo.sp_GetTaxFormData
  @EmployeeNumber NVARCHAR(20),
  @Year INT,
  @FormType NVARCHAR(10)
AS
BEGIN
  SET NOCOUNT ON;
  SELECT TOP(1)
         e.FullName,
         e.EmployeeNumber,
         e.SIN,
         t.[Year],
         t.FormType,
         t.Box14 AS EmploymentIncome,
         t.Box22 AS IncomeTaxDeducted
  FROM dbo.Employees e
  JOIN dbo.TaxSummary t ON t.EmployeeId = e.EmployeeId
  WHERE e.EmployeeNumber = @EmployeeNumber
    AND t.[Year] = @Year
    AND t.FormType = @FormType;
END
GO

/* 4) Test the Setup */
PRINT 'Database setup complete! Running smoke tests...';

PRINT 'Test 1: Alex Martin payslip for March 2022';
EXEC dbo.sp_GetPaystubForRange @EmployeeNumber='102938', @From='2022-03-01', @To='2022-03-31';

PRINT 'Test 2: Jordan Lee T4 for 2023';
EXEC dbo.sp_GetTaxFormData @EmployeeNumber='556677', @Year=2023, @FormType='T4';

PRINT 'Test 3: Sofia Alvarez T4A for 2024';
EXEC dbo.sp_GetTaxFormData @EmployeeNumber='778899', @Year=2024, @FormType='T4A';

PRINT 'Test 4: Check employee disambiguation (both Alex Martins)';
SELECT EmployeeNumber, FullName FROM dbo.Employees WHERE FullName LIKE '%Alex Martin%';

PRINT 'Database setup and testing completed successfully!';
GO
