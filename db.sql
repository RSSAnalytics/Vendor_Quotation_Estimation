-- Vendor Quotation table
DROP DATABASE IF EXISTS vendor_quotation;
CREATE DATABASE IF NOT EXISTS vendor_quotation;
USE vendor_quotation;

----------------------------------------------------
----------------- ADMIN PANEL ----------------------
----------------------------------------------------
-- Admin table
CREATE TABLE IF NOT EXISTS admin (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL
);

-- INSERT INTO admin 
--   (name, password) 
-- VALUES 
--   ("Arun", "Kumar");


----------------------------------------------------
----------------- USER PANEL ----------------------
----------------------------------------------------

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(225) NOT NULL,
  emp_id VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(225) UNIQUE NOT NULL,
  mobile VARCHAR(15) NOT NULL,
  password VARCHAR(255) NOT NULL,
  status ENUM('pending', 'approved') NOT NULL DEFAULT 'pending'
);


----------------------------------------------------
----------------- Categories Model -----------------
----------------------------------------------------

-- Thiruvachi category table
CREATE TABLE IF NOT EXISTS cat_thiruvachi (
  model INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(225) NOT NULL,
  leg_breadth INT NOT NULL,
  sheet_thick INT NOT NULL,
  work_details TEXT NULL,
  cost DECIMAL(10,2) NOT NULL,
  img LONGBLOB NULL,
  img_type VARCHAR(50) NULL
);

-- Kavasam category table
CREATE TABLE IF NOT EXISTS cat_kavasam (
  model INT AUTO_INCREMENT PRIMARY KEY,
  sqft INT UNIQUE NOT NULL, 
  gauge_24 INT NOT NULL DEFAULT 0, 
  gauge_22 INT NOT NULL DEFAULT 0, 
  gauge_20 INT NOT NULL DEFAULT 0, 
  wax_cost INT NOT NULL DEFAULT 0
);
-- Kavasam Rates table
CREATE TABLE IF NOT EXISTS cat_kavasam_rates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  gold_rate INT NOT NULL DEFAULT 0, 
  silver_rate INT NOT NULL DEFAULT 0,
  pure_silver_rate INT NOT NULL DEFAULT 0,
  pure_silver_margin_rate INT NOT NULL DEFAULT 0
);

-- sheet_metal category table
CREATE TABLE IF NOT EXISTS cat_sheet_metal (
  model INT AUTO_INCREMENT PRIMARY KEY,
  heads VARCHAR(225) NOT NULL,
  work_desc VARCHAR(1000) NULL,
  gauge_20__below_21_sqft INT NOT NULL DEFAULT 0,
  gauge_20__21_50_sqft INT NOT NULL DEFAULT 0, 
  gauge_20__above_50_sqft INT NOT NULL DEFAULT 0, 
  gauge_22__below_21_sqft INT NOT NULL DEFAULT 0, 
  gauge_22__21_50_sqft INT NOT NULL DEFAULT 0, 
  gauge_22__above_50_sqft INT NOT NULL DEFAULT 0
);

-- Vahanam category table
CREATE TABLE IF NOT EXISTS cat_vahanam (
  model INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(225) NULL,
  specification VARCHAR(1000) NULL,
  height_1_5ft INT NOT NULL DEFAULT 0,
  height_2ft INT NOT NULL DEFAULT 0,
  height_2_5ft INT NOT NULL DEFAULT 0,
  height_3ft INT NOT NULL DEFAULT 0,
  height_3_5ft INT NOT NULL DEFAULT 0,
  height_4ft INT NOT NULL DEFAULT 0,
  height_5ft INT NOT NULL DEFAULT 0
);

-- Panchaloha Statue category table
CREATE TABLE IF NOT EXISTS cat_panchaloha_statue (
  model INT AUTO_INCREMENT PRIMARY KEY,
  idol_name VARCHAR(225) NOT NULL,
  position VARCHAR(1000) NULL,
  height DECIMAL(5,1) NOT NULL DEFAULT 0,
  hands INT NULL DEFAULT 0,
  with_prabhavalli VARCHAR(225) NULL,
  apx_weight DECIMAL(6,1) NULL DEFAULT 0,
  cost INT NOT NULL DEFAULT 0
);


----------------------------------------------------
------------- INSERT VALUES INTO TABLES ------------
----------------------------------------------------

-- Insert into Thiruvachi table
INSERT INTO cat_thiruvachi (
    name,
    leg_breadth,
    sheet_thick,
    work_details,
    cost
)
VALUES
    ("RGL 26 gauge",      6,  26, "Rgl", 1764),
    ("RRGL 22 Gauge",     6,  22, "Rgl", 3234),
    ("22 Gauge Mid Spl",  7,  22, "Rgl design", 3950),
    ("22 Gauge Spl",      8 , 22, "Rgl design with  Spl 3 ", 4300),
    ("22 Gauge Spl",      10, 22, "Customzed design-drawing to be provided to the customer-after approval we manufactruar", 5600),
    ("22 Gauge",          10, 22, "Customzed design-wit h cut out model,drawing to be provided to the customer-after approval we manufactruar", 6300),
    ("22 Gauge",          12, 20, "Customzed designl,drawing to be provided to the customer-after approval we manufactruar, 3 d model", 9450);


-- Insert into sheet_metal table
INSERT INTO cat_sheet_metal (
    heads,
    work_desc,
    gauge_20__below_21_sqft,
    gauge_20__21_50_sqft,
    gauge_20__above_50_sqft,
    gauge_22__below_21_sqft,
    gauge_22__21_50_sqft,
    gauge_22__above_50_sqft
)
VALUES
    ('Nilai Padi - 20% Picture',	'Drawing to be provided to the customer and Get Approval-After Plan to Make As per the Drawing', 3000, 2750, 2500, 2600, 2400, 2200),
    ('Nila Padi Normal + Vargam + 20% Picture', 'Drawing to be provided to the customer and Get Approval-After Plan to Make As per the Drawing', 3500, 3000, 2750, 3100, 2600, 2400),
    ('Addinal Customized Picture per Sqft', 'Drawing to be provided to the customer and Get Approval-After Plan to Make As per the Drawing', 2000, 2000, 2000, 2000, 2000, 2000);


-- Insert into Kavasam table
INSERT INTO cat_kavasam (
    sqft,
    gauge_24,
    gauge_22,
    gauge_20,
    wax_cost
)
VALUES
    (1, 5000, 6000, 7000, 1500),
    (2, 4500, 5500, 6500, 1500),
    (3, 4500, 5500, 6500, 1500),
    (4, 4000, 5000, 6000, 2000),
    (5, 4000, 5000, 6000, 2000),
    (6, 4000, 5000, 6000, 2000),
    (7, 4000, 5000, 6000, 2000),
    (8, 4000, 5000, 6000, 2000),
    (9, 3750, 4500, 5500, 4000),
    (10, 3750, 4500, 5500, 4000),
    (11, 3750, 4500, 5500, 4000),
    (12, 3750, 4500, 5500, 5000),
    (13, 3750, 4500, 5500, 5000),
    (14, 3750, 4500, 5500, 5000),
    (15, 3750, 4500, 5500, 5000);

-- Insert into Kavasam Rates table
INSERT INTO cat_kavasam_rates (
    gold_rate,
    silver_rate,
    pure_silver_rate,
    pure_silver_margin_rate
)
VALUES
    (9000, 2250, 254, 46);


-- Insert into Vahanam table
INSERT INTO cat_vahanam (
    name,
    specification,
    height_1_5ft,
    height_2ft,
    height_2_5ft,
    height_3ft,
    height_3_5ft,
    height_4ft,
    height_5ft
)
VALUES
    ('Rishabam', 'Standing -with Based beedam and Swany sitting stand', 32000, 48000, 72000, 88000, 123200, 172480, 241472),
    ('Simmam', 'Standing -with Based beedam and Swany sitting stand', 32000, 48000, 72000, 88000, 123200, 172480, 241472),
    ('Horse', 'Standing -with Based beedam and Swany sitting stand', 32000, 48000, 72000, 88000, 123200, 172480, 241472),
    ('Munchur', 'Standing -with Based beedam and Swany sitting stand', 32000, 48000, 72000, 88000, 123200, 172480, 241472),
    ('Garudan', 'Standing -with Based beedam and Swany sitting stand', 32000, 48000, 72000, 88000, 123200, 172480, 241472),
    ('Hanuman', 'Standing -with Based beedam and Swany sitting stand', 32000, 48000, 72000, 88000, 123200, 172480, 241472),
    ('Suran', 'Standing -with Based beedam-3 faces Detachable', 38400, 57600, 86400, 105600, 147840, 206976, 289766),
    ('Goat', 'Standing -with Based beedam and Swany sitting stand', 32000, 48000, 72000, 88000, 123200, 172480, 241472),
    ('Puli' ,' Standing -with Based beedam and Swany sitting stand', 32000, 48000, 72000, 88000, 123200, 172480, 241472),
    ('Elephant', 'Standing -with Based beedam and Swany sitting stand', 44800, 62400, 93600, 114400, 160160, 224224, 313914),
    ('Annam', 'Standing -with Based beedam and Swany sitting stand', 41600, 64800, 97200, 118800, 166320, 232848, 325987),
    ('Peacock', 'Standing -with Based beedam and Swany sitting stand', 41600, 64800, 97200, 118800, 166320, 232848, 325987),
    ('Snake' ,' Five face head--base beedam', 44800, 62400, 93600, 114400, 160160, 224224, 313913),
    ('Suriya Brabai', 'Suriyan base with Arch-with Beedam-with 7 horse and Choriater', 49920, 77760, 116640, 142560, 199584, 279417, 391184),
    ('Chandra Brabai', 'Chandran  base  with Arch-with Beedam', 32000, 48000, 72000, 88000, 123200, 172480, 241472);


-- Insert into Panchaloha Statue table
INSERT INTO cat_panchaloha_statue (
  idol_name,
  position,
  height,
  hands,
  with_prabhavalli,
  apx_weight,
  cost
)
VALUES
  ('Pradashoa Murthy', 'Sitting With Cow With Pravathi', 12, 4, 'yes', 5, 21492),
  ('Pradashoa Murthy', 'Sitting With Cow With Pravathi', 15, 4, 'yes', 7, 36036),
  ('Pradashoa Murthy', 'Sitting With Cow With Pravathi', 18, 4, 'yes', 9, 61776),
  ('Valampuri Ganesh', 'Standing', 6, 4, 'No', 0, 4504),
  ('Valampuri Ganesh', 'Standing', 9, 4, 'No', 0, 9845),
  ('Valampuri Ganesh', 'Standing', 12, 4, 'No', 0, 16116),
  ('Valampuri Ganesh', 'Standing', 15, 4, 'No', 0, 21235),
  ('Valampuri Ganesh', 'Standing', 18, 4, 'No', 0, 41886),
  ('Valampuri Ganesh', 'Standing', 21, 4, 'No', 0, 50473),
  ('Valampuri Ganesh', 'Standing', 24, 4, 'No', 0, 75516),
  ('Valampuri Ganesh', 'Standing', 30, 4, 'No', 0, 111969),
  ('Edampuri Ganesh', 'Standing', 6, 4, 'No', 0, 4185),
  ('Edampuri Ganesh', 'Standing', 9, 4, 'No', 0, 9845),
  ('Edampuri Ganesh', 'Standing', 12, 4, 'No', 0, 12226),
  ('Edampuri Ganesh', 'Standing', 15, 4, 'No', 0, 21235),
  ('Edampuri Ganesh', 'Standing', 18, 4, 'No', 0, 34611),
  ('Edampuri Ganesh', 'Standing', 21, 4, 'No', 0, 55491),
  ('Edampuri Ganesh', 'Standing', 24, 4, 'No', 0, 74646),
  ('Edampuri Ganesh', 'Standing', 30, 4, 'No', 0, 111969),
  ('Ganesh', 'Sitting', 6, 2, 'yes', 0, 4742),
  ('Ganesh', 'Sitting', 9, 2, 'yes', 0, 13191),
  ('Ganesh', 'Sitting', 12, 2, 'yes', 0, 18357),
  ('Ganesh', 'Sitting', 15, 2, 'yes', 0, 33600),
  ('Ganesh', 'Sitting', 18, 2, 'yes', 0, 53416),
  ('Ganesh', 'Sitting', 21, 2, 'yes', 0, 70235),
  ('Ganesh', 'Sitting', 24, 2, 'yes', 0, 91640),
  ('Ganesh', 'Sitting', 30, 2, 'yes', 0, 116795),
  ('Dancing Ganesh', 'Standing', 9, 4, 'No', 0, 11583),
  ('Dancing Ganesh', 'Standing', 12, 4, 'No', 0, 16087),
  ('Dancing Ganesh', 'Standing', 18, 4, 'No', 0, 52767),
  ('Mooshika Ganesh', 'Sitting On Rat', 9, 4, 'No', 0, 12226),
  ('Mooshika Ganesh', 'Sitting On Rat', 12, 4, 'No', 0, 27027),
  ('Mooshika Ganesh', 'Sitting On Rat', 18, 4, 'No', 0, 48262),
  ('Perumal With Sridevi Bhudevi', 'Standing', 6, 8, 'No', 0, 10348),
  ('Perumal With Sridevi Bhudevi', 'Standing', 9, 8, 'No', 0, 16934),
  ('Perumal With Sridevi Bhudevi', 'Standing', 12, 8, 'No', 0, 26342),
  ('Perumal With Sridevi Bhudevi', 'Standing', 15, 8, 'No', 0, 32175),
  ('Perumal With Sridevi Bhudevi', 'Standing', 18, 8, 'No', 0, 42128),
  ('Perumal With Sridevi Bhudevi', 'Standing', 21, 8, 'No', 0, 58935),
  ('Perumal With Sridevi Bhudevi', 'Standing', 24, 8, 'No', 0, 84224),
  ('Perumal With Sridevi Bhudevi Single Peedam', 'Standing', 15, 8, 'No', 0, 38000),
  ('Rama Set', 'Standing', 12, 8, 'No', 0, 27636),
  ('Rama Set', 'Standing', 15, 8, 'No', 0, 41395),
  ('Rama Set', 'Standing', 18, 8, 'No', 0, 51744),
  ('Rama Set', 'Standing', 21, 8, 'No', 0, 69266),
  ('Rama Set', 'Standing', 24, 8, 'No', 0, 112225),
  ('Muruga With Valli Deivani', 'Standing', 6, 8, 'No', 0, 10348),
  ('Muruga With Valli Deivani', 'Standing', 9, 8, 'No', 0, 19192),
  ('Muruga With Valli Deivani', 'Standing', 12, 8, 'No', 0, 27053),
  ('Muruga With Valli Deivani', 'Standing', 15, 8, 'No', 0, 37709),
  ('Muruga With Valli Deivani', 'Standing', 18, 8, 'No', 0, 46954),
  ('Muruga With Valli Deivani', 'Standing', 21, 8, 'No', 0, 63875),
  ('Muruga With Valli Deivani', 'Standing', 24, 8, 'No', 0, 88867),
  ('Bala Murugar', 'Standing', 9, 2, 'No', 0, 9979),
  ('Bala Murugar', 'Standing', 12, 2, 'No', 0, 12230),
  ('Natarajar', 'Standing', 6, 4, 'yes', 0, 8400),
  ('Natarajar', 'Standing', 9, 4, 'yes', 0, 12561),
  ('Natarajar', 'Standing', 12, 4, 'yes', 0, 17404),
  ('Natarajar', 'Standing', 15, 4, 'yes', 0, 18661),
  ('Natarajar', 'Standing', 18, 4, 'yes', 0, 28312),
  ('Natarajar', 'Standing', 21, 4, 'yes', 0, 39514),
  ('Natarajar', 'Standing', 24, 4, 'yes', 0, 45293),
  ('Ayyappan', 'Sitting', 6, 2, 'yes', 0, 6113),
  ('Ayyappan', 'Sitting', 9, 2, 'yes', 0, 10939),
  ('Ayyappan', 'Sitting', 12, 2, 'yes', 0, 17875),
  ('Ayyappan', 'Sitting', 18, 2, 'yes', 0, 42266),
  ('Ayyappan', 'Sitting', 21, 2, 'yes', 0, 58723),
  ('Ayyappan', 'Sitting', 24, 2, 'yes', 0, 71970),
  ('Kamatchi', 'Sitting', 6, 4, 'yes', 0, 5014),
  ('Kamatchi', 'Sitting', 9, 4, 'yes', 0, 12800),
  ('Kamatchi', 'Sitting', 12, 4, 'yes', 0, 16425),
  ('Lakshmi', 'Sitting', 6, 4, 'yes', 0, 4697),
  ('Lakshmi', 'Sitting', 9, 4, 'yes', 0, 13256),
  ('Lakshmi', 'Sitting', 12, 4, 'yes', 0, 16425),
  ('Lakshmi', 'Sitting', 15, 4, 'yes', 0, 22522),
  ('Lakshmi', 'Sitting', 18, 4, 'yes', 0, 37966),
  ('Raja Rajeshwari', 'Sitting', 6, 4, 'yes', 0, 4697),
  ('Raja Rajeshwari', 'Sitting', 9, 4, 'yes', 0, 13256),
  ('Raja Rajeshwari', 'Sitting', 12, 4, 'yes', 0, 16425),
  ('Raja Rajeshwari', 'Sitting', 15, 4, 'yes', 0, 28986),
  ('Mariamman', 'Sitting', 6, 4, 'yes', 0, 4896),
  ('Mariamman', 'Sitting', 9, 4, 'yes', 0, 13256),
  ('Mariamman', 'Sitting', 12, 4, 'yes', 0, 17875),
  ('Mariamman', 'Sitting', 15, 4, 'yes', 0, 22522),
  ('Mariamman', 'Sitting', 18, 4, 'yes', 0, 41461),
  ('Mariamman', 'Sitting', 21, 4, 'yes', 0, 65617),
  ('Mariamman', 'Sitting', 24, 4, 'yes', 0, 90310),
  ('Azhwarkal', 'Sitting', 4, 24, 'No', 0, 69000),
  ('Azhwarkal', 'Sitting', 5, 24, 'No', 0, 75900),
  ('Azhwarkal', 'Sitting', 6, 24, 'No', 0, 90100),
  ('Chkarathzvar', 'Standing', 10, 0, 'yes', 0, 20697),
  ('Chkarathzvar', 'Standing', 12, 0, 'yes', 0, 25000),
  ('Chkarathzvar', 'Standing', 15, 0, 'yes', 0, 35000),
  ('Chkarathzvar', 'Standing', 18, 0, 'yes', 0, 51600),
  ('Hanuman', 'Standing', 9, 2, 'No', 0, 8558),
  ('Hanuman', 'Standing', 12, 2, 'No', 0, 12226),
  ('Shiva And Parvati', 'Standing', 12, 6, 'No', 0, 21600),
  ('Shiva And Parvati', 'Standing', 18, 6, 'No', 0, 38500),
  ('Shiva And Parvati', 'Standing', 21, 6, 'No', 0, 42184),
  ('Shiva And Parvati', 'Standing', 24, 6, 'No', 0, 55976),
  ('Shiva And Parvati', 'Standing', 12, 6, 'yes', 0, 19948),
  ('Shiva And Parvati', 'Standing', 18, 6, 'yes', 0, 28442),
  ('Shiva And Parvati', 'Standing', 21, 6, 'yes', 0, 40540),
  ('Shiva And Parvati', 'Standing', 24, 6, 'yes', 0, 54697),
  ('Nalvar Set', 'Standing', 6, 8, 'No', 0, 15444),
  ('Nalvar Set', 'Standing', 10, 8, 'No', 0, 41395),
  ('Nalvar Set', 'Standing', 12, 8, 'No', 0, 48000),
  ('Sai Baba', 'Sitting', 4, 2, 'No', 0, 6058),
  ('Sai Baba', 'Sitting', 5, 2, 'No', 0, 7059),
  ('Sai Baba', 'Sitting', 6, 2, 'No', 0, 8080),
  ('Lakshmi Narasimhar', 'Sitting', 5, 6, 'No', 0, 10296),
  ('Lakshmi Narasimhar', 'Sitting', 9, 6, 'No', 0, 18018),
  ('Varahi Amman', 'Sitting', 5, 8, 'No', 0, 6542),
  ('Varahi Amman', 'Sitting', 9, 8, 'No', 0, 18816),
  ('Satyanarayana', 'Standing', 12, 4, 'No', 0, 16647),
  ('Sarabeswarar', '', 6, 0, 'No', 0, 16139),
  ('Durga Devi', 'Standing', 12, 18, 'No', 0, 39639),
  ('Bhairava', 'Standing With Dog', 12, 4, 'No', 0, 12230),
  ('Narashimar', 'Standing', 12, 4, 'No', 0, 17696),
  ('Panchamukha Hanuman', 'Standing', 12, 8, 'No', 0, 31853),
  ('Ramanujar', 'Sitting', 12, 2, 'No', 0, 24774),
  ('Kanchi Maha Periyava', 'Sitting', 6, 2, 'No', 0, 24000),
  ('Kanchi Maha Periyava', 'Sitting', 9, 2, 'No', 0, 28000),
  ('Swarna Akarshana Bhairava', 'Sitting', 5, 6, 'No', 0, 7551),
  ('Swarna Akarshana Bhairava', 'Sitting', 9, 6, 'No', 0, 20160),
  ('Lingam And Nandhi', '', 4, 0, 'No', 0, 10381),
  ('Kamadhenu', '', 8.5, 0, '', 0, 7395),
  ('Lakshmi Varahi', 'Sitting', 6, 6, 'No', 0, 6472),
  ('Murugar Set', 'Standing', 23, 8, 'yes', 0, 16044),
  ('Prithiyangara Devi', 'Sitting', 7.5, 4, 'No', 0, 12230),
  ('Andal', 'Standing', 6, 2, 'No', 0, 5258),
  ('Poigai Azhwar', 'Standing', 6, 2, 'No', 0, 5663),
  ('Periyazhwar', 'Sitting', 4, 2, 'No', 0, 5663),
  ('Thirumazhisai Azhwar', 'Sitting', 4, 2, 'No', 0, 5663),
  ('Bhoothnath Azhwar', 'Standing', 5, 2, 'No', 0, 5663),
  ('Thondarath Azhwar', 'Standing', 5, 2, 'No', 0, 5663),
  ('Thirupazhwar', 'Standing', 5, 2, 'No', 0, 5662),
  ('Kulasekara Azhwar', 'Standing', 5, 2, 'No', 0, 5663),
  ('Perumal Set', 'Standing', 27, 8, 'yes', 0, 16044),
  ('Shivalingam', '', 15, 0, '', 0, 84000);