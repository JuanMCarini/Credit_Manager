-- Drop database
DROP DATABASE IF EXISTS credit_manager;

-- Create the database if it does not exist
CREATE DATABASE IF NOT EXISTS credit_manager;

-- Select the database to use
USE credit_manager;

-- Table: Business Partners
CREATE TABLE business_partners (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Name VARCHAR(255), CUIT VARCHAR(20) UNIQUE, Email VARCHAR(100), Active BOOLEAN NOT NULL DEFAULT 1);

-- Table: Purchases
CREATE TABLE purchases (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Date DATE, APR DECIMAL(22,6), Resource BOOLEAN, VAT BOOLEAN, Supplier_ID INT, FOREIGN KEY (Supplier_ID) REFERENCES business_partners(ID));

-- Table: Sales
CREATE TABLE sales (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Date DATE, APR DECIMAL(22,6), Resource BOOLEAN, VAT BOOLEAN, Client_ID INT, FOREIGN KEY (Client_ID) REFERENCES business_partners(ID));

-- Categorical tables
CREATE TABLE genders (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Description VARCHAR(50) UNIQUE);
CREATE TABLE marital_status (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Description VARCHAR(100) UNIQUE);

-- 1) Dimension tables
CREATE TABLE countries (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Name VARCHAR(100) UNIQUE, Nationality VARCHAR(100) UNIQUE);

CREATE TABLE provinces (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Name VARCHAR(100), Country_ID INT, FOREIGN KEY (Country_ID) REFERENCES countries(ID));

CREATE TABLE cities (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Name VARCHAR(100), Province_ID INT NOT NULL, FOREIGN KEY (Province_ID) REFERENCES provinces(ID));

-- 2) Clients (use INT for the FK types, and remove quotes in REFERENCES)
CREATE TABLE clients (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Last_Name VARCHAR(100), First_Name VARCHAR(100), DNI VARCHAR(20) UNIQUE, CUIL VARCHAR(20) UNIQUE, Birth_Date DATE, Gender_ID INT, Marital_Status_ID INT, Nationality_ID INT, Province_ID INT, City_ID INT, Address VARCHAR(255), Email VARCHAR(100), Status_Date DATE, Active BOOLEAN NOT NULL DEFAULT 1, FOREIGN KEY (Gender_ID) REFERENCES genders(ID), FOREIGN KEY (Marital_Status_ID) REFERENCES marital_status(ID), FOREIGN KEY (Nationality_ID) REFERENCES countries(ID), FOREIGN KEY (Province_ID) REFERENCES provinces(ID), FOREIGN KEY (City_ID) REFERENCES cities(ID));

-- 3) Employment status (align FK types and remove quotes)
CREATE TABLE employment_status (ID INT PRIMARY KEY AUTO_INCREMENT, Client_ID INT NOT NULL, Employer VARCHAR(255), Employer_TIN VARCHAR(20), Seniority INT, Monthly_Income DECIMAL(12, 2), Province_ID INT, City_ID INT, Address VARCHAR(255), Start_Date DATE, End_Date DATE, FOREIGN KEY (Client_ID) REFERENCES clients(ID), FOREIGN KEY (Province_ID) REFERENCES provinces(ID), FOREIGN KEY (City_ID) REFERENCES cities(ID));

-- Table: Additional Addresses
CREATE TABLE additional_addresses (ID INT PRIMARY KEY AUTO_INCREMENT, Client_ID INT, Description VARCHAR(500), FOREIGN KEY (Client_ID) REFERENCES clients(ID));

-- Table: Phones
CREATE TABLE phones (ID INT PRIMARY KEY AUTO_INCREMENT, Client_ID INT, Number VARCHAR(50), Type VARCHAR(50), Relationship VARCHAR(50), FOREIGN KEY (Client_ID) REFERENCES clients(ID));

-- Table: Credit Types
CREATE TABLE credit_types (ID INT PRIMARY KEY AUTO_INCREMENT, Name VARCHAR(50) UNIQUE);

-- Table: Lines
CREATE TABLE business_lines (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Name VARCHAR(255) UNIQUE, CUIT VARCHAR(20) UNIQUE, Abbreviation VARCHAR(10) UNIQUE, Email VARCHAR(100), Active BOOLEAN NOT NULL DEFAULT 1);

-- Table: Organisms
CREATE TABLE organisms (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Name VARCHAR(255) UNIQUE, CUIT VARCHAR(20) UNIQUE, Line_ID INT, City_ID INT, Email VARCHAR(100), Active BOOLEAN NOT NULL DEFAULT 1, FOREIGN KEY (Line_ID) REFERENCES business_lines(ID), FOREIGN KEY (City_ID) REFERENCES cities(ID));

-- Table: Credits
CREATE TABLE credits (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Origin_ID INT, Disbursement_Date DATE, First_Due_Date DATE, Amount_Disbursed DECIMAL(22,6), Capital DECIMAL(22,6), Credit_Type_ID INT, TNA_C_IVA DECIMAL(22,6), Term INT, Client_ID INT, Organism_ID INT, Purchase_ID INT, Sale_ID INT, FOREIGN KEY (Credit_Type_ID) REFERENCES credit_types(ID), FOREIGN KEY (Client_ID) REFERENCES clients(ID), FOREIGN KEY (Organism_ID) REFERENCES organisms(ID), FOREIGN KEY (Purchase_ID) REFERENCES purchases(ID), FOREIGN KEY (Sale_ID) REFERENCES sales(ID));

-- Table: Installments
CREATE TABLE installments (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Credit_ID INT, Inst_Num INT, Owner_ID INT, Due_Date DATE, Capital DECIMAL(22,6), Interest DECIMAL(22,6), IVA DECIMAL(22,6), Total DECIMAL(22,6), Settlement_Date DATE, FOREIGN KEY (Credit_ID) REFERENCES credits(ID), FOREIGN KEY (Owner_ID) REFERENCES business_partners(ID));

-- Table: Collection Types
CREATE TABLE collection_types (ID INT PRIMARY KEY AUTO_INCREMENT, Type VARCHAR(100));

-- Table: Collections
CREATE TABLE collections (ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT, Installment_ID INT, Date DATE, Type_ID INT, Capital DECIMAL(22,6), Interest DECIMAL(22,6), IVA DECIMAL(22,6), Total DECIMAL(22,6), FOREIGN KEY (Installment_ID) REFERENCES installments(ID), FOREIGN KEY (Type_ID) REFERENCES collection_types(ID));