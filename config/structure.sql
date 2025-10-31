-- Create the database if it does not exist
CREATE DATABASE IF NOT EXISTS credit_manager;

-- Select the database to use
USE credit_manager;

-- Drop tables if they exist
DROP TABLE IF EXISTS collections;
DROP TABLE IF EXISTS collection_type;
DROP TABLE IF EXISTS installments;
DROP TABLE IF EXISTS credits;
DROP TABLE IF EXISTS phones;
DROP TABLE IF EXISTS additional_addresses;
DROP TABLE IF EXISTS employment_status;
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS cities;
DROP TABLE IF EXISTS provinces;
DROP TABLE IF EXISTS countries;
DROP TABLE IF EXISTS gender;
DROP TABLE IF EXISTS marital_status;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS purchases;
DROP TABLE IF EXISTS credit_type;
DROP TABLE IF EXISTS business_partners;

-- Table: Business Partners
CREATE TABLE business_partners (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Company_Name VARCHAR(255), CUIL VARCHAR(20) UNIQUE, Email VARCHAR(100));

-- Table: Purchases
CREATE TABLE purchases (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Date DATE, APR FLOAT, Resource BOOLEAN, VAT BOOLEAN, Supplier_ID INT, FOREIGN KEY (Supplier_ID) REFERENCES business_partners(ID));

-- Table: Sales
CREATE TABLE sales (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Date DATE, APR FLOAT, Resource BOOLEAN, VAT BOOLEAN, Client_ID INT, FOREIGN KEY (Client_ID) REFERENCES business_partners(ID));

-- Categorical tables
CREATE TABLE gender (ID INT PRIMARY KEY, Description VARCHAR(50) UNIQUE);
CREATE TABLE marital_status (ID INT PRIMARY KEY, Description VARCHAR(100) UNIQUE);

-- 1) Dimension tables
CREATE TABLE countries (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Name VARCHAR(100) UNIQUE, Nationality VARCHAR(100) UNIQUE);

CREATE TABLE provinces (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Name VARCHAR(100) UNIQUE);
CREATE TABLE cities (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Province_ID INT NOT NULL, Name VARCHAR(100) UNIQUE, FOREIGN KEY (Province_ID) REFERENCES provinces(ID));

-- 2) Clients (use INT for the FK types, and remove quotes in REFERENCES)
CREATE TABLE clients (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Last_Name VARCHAR(100), First_Name VARCHAR(100), DNI VARCHAR(20) UNIQUE, CUIL VARCHAR(20) UNIQUE, Birth_Date DATE, Gender_ID INT, Marital_Status_ID INT, Nationality_ID INT, Province_ID INT, City_ID INT, Address VARCHAR(255), Email VARCHAR(100), Status_Date DATE, FOREIGN KEY (Gender_ID) REFERENCES gender(ID), FOREIGN KEY (Marital_Status_ID) REFERENCES marital_status(ID), FOREIGN KEY (Nationality_ID) REFERENCES countries(ID), FOREIGN KEY (Province_ID) REFERENCES provinces(ID), FOREIGN KEY (City_ID) REFERENCES cities(ID));

-- 3) Employment status (align FK types and remove quotes)
CREATE TABLE employment_status (ID INT PRIMARY KEY AUTO_INCREMENT, Client_ID INT NOT NULL, Employer VARCHAR(255), Employer_TIN VARCHAR(20), Seniority INT, Monthly_Income DECIMAL(12, 2), Province_ID INT, City_ID INT, Address VARCHAR(255), Start_Date DATE, End_Date DATE, FOREIGN KEY (Client_ID) REFERENCES clients(ID), FOREIGN KEY (Province_ID) REFERENCES provinces(ID), FOREIGN KEY (City_ID) REFERENCES cities(ID));

-- Table: Additional Addresses
CREATE TABLE additional_addresses (ID INT PRIMARY KEY AUTO_INCREMENT, Client_ID INT, Description VARCHAR(500), FOREIGN KEY (Client_ID) REFERENCES clients(ID));

-- Table: Phones
CREATE TABLE phones (ID INT PRIMARY KEY AUTO_INCREMENT, Client_ID INT, Number VARCHAR(50), Type VARCHAR(50), Relationship VARCHAR(50), FOREIGN KEY (Client_ID) REFERENCES clients(ID));

-- Table: Credit Types
CREATE TABLE credit_type (ID INT PRIMARY KEY, Type VARCHAR(50));

-- Table: Credits
CREATE TABLE credits (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Origin_ID INT, Disbursement_Date DATE, First_Due_Date DATE, Amount_Disbursed FLOAT, Principal FLOAT, Credit_Type_ID INT, APR_with_VAT FLOAT, Term INT, Installment_Value FLOAT, Client_ID INT, Purchase_ID INT, Sale_ID INT, FOREIGN KEY (Credit_Type_ID) REFERENCES credit_type(ID), FOREIGN KEY (Client_ID) REFERENCES clients(ID), FOREIGN KEY (Purchase_ID) REFERENCES purchases(ID), FOREIGN KEY (Sale_ID) REFERENCES sales(ID));

-- Table: Installments
CREATE TABLE installments (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Credit_ID INT, Installment_Number INT, Owner_ID INT, Due_Date DATE, Principal FLOAT, Interest FLOAT, VAT FLOAT, Total FLOAT, Settlement_Date DATE, FOREIGN KEY (Credit_ID) REFERENCES credits(ID), FOREIGN KEY (Owner_ID) REFERENCES business_partners(ID));

-- Table: Collection Types
CREATE TABLE collection_type (ID INT PRIMARY KEY, Type VARCHAR(100));

-- Table: Collections
CREATE TABLE collections (ID INT PRIMARY KEY, Installment_ID INT, Date DATE, Type_ID INT, Principal FLOAT, Interest FLOAT, VAT FLOAT, Total FLOAT, FOREIGN KEY (Installment_ID) REFERENCES installments(ID), FOREIGN KEY (Type_ID) REFERENCES collection_type(ID));