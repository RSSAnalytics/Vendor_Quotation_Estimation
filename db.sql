-- #######################################
-- ############### DATABASE ##############
-- #######################################
-- DROP DATABASE IF EXISTS vendor_quotation;
-- CREATE DATABASE IF NOT EXISTS vendor_quotation;
USE defaultdb;

-- SET FOREIGN_KEY_CHECKS = 0;

-- DROP TABLE IF EXISTS `master_quotation_items`;
-- DROP TABLE IF EXISTS `master_quotations`;
-- DROP TABLE IF EXISTS `quotations`;
-- DROP TABLE IF EXISTS `quot_thiruvachi`;
-- DROP TABLE IF EXISTS `quot_kavasam`;
-- DROP TABLE IF EXISTS `quot_vahanam`;
-- DROP TABLE IF EXISTS `quot_kodimaram`;
-- DROP TABLE IF EXISTS `quot_sheet_metal`;
-- DROP TABLE IF EXISTS `quot_panchaloha_statue`;
-- DROP TABLE IF EXISTS `cat_thiruvachi_images`;
-- DROP TABLE IF EXISTS `cat_thiruvachi_rates`;
-- DROP TABLE IF EXISTS `cat_thiruvachi`;
-- DROP TABLE IF EXISTS `cat_kavasam_images`;
-- DROP TABLE IF EXISTS `cat_kavasam_rates`;
-- DROP TABLE IF EXISTS `cat_kavasam`;
-- DROP TABLE IF EXISTS `cat_vahanam_images`;
-- DROP TABLE IF EXISTS `cat_vahanam`;
-- DROP TABLE IF EXISTS `cat_sheet_metal_images`;
-- DROP TABLE IF EXISTS `cat_sheet_metal`;
-- DROP TABLE IF EXISTS `cat_panchaloha_statue_images`;
-- DROP TABLE IF EXISTS `cat_panchaloha_statue`;
-- DROP TABLE IF EXISTS `cat_kodimaram_images`;
-- DROP TABLE IF EXISTS `customers`;
-- DROP TABLE IF EXISTS `users`;
-- DROP TABLE IF EXISTS `admin`;

-- SET FOREIGN_KEY_CHECKS = 1;

-- #######################################
-- ############# ADMIN TABLE #############
-- #######################################
CREATE TABLE IF NOT EXISTS admin (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL
);

INSERT INTO admin (name, password) VALUES ('admin', 'admin');


-- #######################################
-- ############# USER TABLE ##############
-- #######################################
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(225) NOT NULL,
  emp_id VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(225) UNIQUE NOT NULL,
  mobile VARCHAR(15) NOT NULL,
  password VARCHAR(255) NOT NULL,
  branch VARCHAR(255) NOT NULL,
  status ENUM('pending', 'approved') NOT NULL DEFAULT 'pending'
);

-- INSERT INTO users 
--   (name, emp_id, email, mobile, password, branch, status) 
-- VALUES 
--   ("a", "a", "a@gmail.com", 1, "a", "Kanchipuram", "approved");



-- #######################################
-- ########### CUSTOMERS TABLE ###########
-- #######################################
CREATE TABLE IF NOT EXISTS customers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(225) NOT NULL,
  mobile VARCHAR(15) UNIQUE NOT NULL,
  temple VARCHAR(1000) NULL,
  address VARCHAR(1000) NULL,
  user_emp_id VARCHAR(255) NOT NULL,
  updated_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- INSERT INTO customers 
--   (name, mobile, temple, address, user_emp_id) 
-- VALUES 
--   ("customer 1", '9999999999', "temple 1", "address 1", "a"),
--   ("customer 2", '8888888888', "temple 2", "address 2", "a"),
--   ("customer 3", '7777777777', "temple 3", "address 3", "a");


-- #######################################
-- ########### QUOTATION TABLES ##########
-- #######################################

CREATE TABLE IF NOT EXISTS quotations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  category VARCHAR(225) NULL,
  quot_id INT NOT NULL,
  user_emp_id VARCHAR(255) NOT NULL,
  cust_id INT NOT NULL
);


CREATE TABLE master_quotations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  quotation_no VARCHAR(50) UNIQUE NOT NULL,
  user_emp_id VARCHAR(255) NOT NULL,
  cust_id INT NOT NULL,
  total_SQFT DECIMAL(10,2) NOT NULL,
  total_cost INT NOT NULL,
  total_transport INT NOT NULL,
  grand_total INT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE master_quotation_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  master_quotation_id INT NOT NULL,
  quotation_id INT NOT NULL,

  FOREIGN KEY (master_quotation_id)
    REFERENCES master_quotations(id)
    ON DELETE CASCADE,

  FOREIGN KEY (quotation_id)
    REFERENCES quotations(id)
    ON DELETE CASCADE
);



-- ############## THIRUVACHI ##############
CREATE TABLE IF NOT EXISTS quot_thiruvachi (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_emp_id VARCHAR(255) NOT NULL,
  cust_id INT NOT NULL,
  model_id INT NOT NULL,
  material VARCHAR(225) NOT NULL,
  leg_breadth INT NOT NULL,
  sheet_thick INT NOT NULL,
  work_type ENUM('Regular', 'Customized') NOT NULL DEFAULT 'Regular',
  work_details VARCHAR(1000) NOT NULL,
  SQFT DECIMAL(10,2) NOT NULL,
  unit INT NOT NULL DEFAULT 1,
  cost INT NOT NULL,
  transport_cost INT NOT NULL,
  delivery_days VARCHAR(225) NOT NULL,
  validity_days VARCHAR(225) NOT NULL
);


-- ############## KAVASAM ##############
CREATE TABLE IF NOT EXISTS quot_kavasam (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_emp_id VARCHAR(255) NOT NULL,
  cust_id INT NOT NULL,
  material VARCHAR(225) NOT NULL,
  sheet_thick INT NOT NULL,
  SQFT DECIMAL(10,2) NOT NULL,
  unit INT NOT NULL DEFAULT 1,
  cost INT NOT NULL,
  wax_cost INT NOT NULL,
  transport_cost INT NOT NULL,
  delivery_days VARCHAR(225) NOT NULL,
  validity_days VARCHAR(225) NOT NULL
);


-- ############## VAHANAM ##############
CREATE TABLE IF NOT EXISTS quot_vahanam (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_emp_id VARCHAR(255) NOT NULL,
  cust_id INT NOT NULL,
  name VARCHAR(225) NOT NULL,
  specification VARCHAR(225) NOT NULL,
  material VARCHAR(225) NOT NULL,
  height DECIMAL(10,2) NOT NULL,
  unit INT NOT NULL DEFAULT 1,
  cost INT NOT NULL,
  transport_cost INT NOT NULL,
  delivery_days VARCHAR(225) NOT NULL,
  validity_days VARCHAR(225) NOT NULL
);


-- ############## KODIMARAM ##############
CREATE TABLE IF NOT EXISTS quot_kodimaram (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_emp_id VARCHAR(255) NOT NULL,
  cust_id INT NOT NULL,
  height DECIMAL(10,2) NOT NULL,
  diameter DECIMAL(10,2) NOT NULL,
  SQFT DECIMAL(10,2) NOT NULL,
  weight DECIMAL(10,2) NOT NULL,
  unit INT NOT NULL DEFAULT 1,
  cost INT NOT NULL,
  transport_cost INT NOT NULL,
  delivery_days VARCHAR(225) NOT NULL,
  validity_days VARCHAR(225) NOT NULL
);


-- ############## SHEET METAL ##############
CREATE TABLE IF NOT EXISTS quot_sheet_metal (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_emp_id VARCHAR(255) NOT NULL,
  cust_id INT NOT NULL,
  material VARCHAR(225) NOT NULL,
  thickness VARCHAR(225) NOT NULL,
  nilai_padi_plain_total_SQFT DECIMAL(10,2) NOT NULL DEFAULT 0,
  nilai_padi_vargam_total_SQFT DECIMAL(10,2) NOT NULL DEFAULT 0,
  custom_picture_total_SQFT DECIMAL(10,2) NOT NULL DEFAULT 0,
  nilai_padi_plain_unit INT NULL DEFAULT 1,
  nilai_padi_vargam_unit INT NULL DEFAULT 1,
  custom_picture_unit INT NULL DEFAULT 1,
  nilai_padi_plain_final_cost INT NULL DEFAULT 0,
  nilai_padi_vargam_final_cost INT NULL DEFAULT 0,
  custom_picture_final_cost INT NULL DEFAULT 0,
  transport_cost INT NOT NULL,
  delivery_days VARCHAR(225) NOT NULL,
  validity_days VARCHAR(225) NOT NULL
);


-- ############## PANCHALOHA STATUE ##############
CREATE TABLE IF NOT EXISTS quot_panchaloha_statue (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_emp_id VARCHAR(255) NOT NULL,
  cust_id INT NOT NULL,
  name VARCHAR(225) NOT NULL,
  prabavali VARCHAR(225) NOT NULL,
  position VARCHAR(225) NOT NULL,
  model VARCHAR(225) NOT NULL,
  hands INT NOT NULL,
  height INT NOT NULL,
  weight INT NOT NULL,
  unit INT NOT NULL,
  cost INT NOT NULL,
  transport_cost INT NOT NULL,
  delivery_days VARCHAR(225) NOT NULL,
  validity_days VARCHAR(225) NOT NULL
);



-- #######################################################
-- ############### CATEGORY TABLE CREATION ###############
-- #######################################################

-- ############## THIRUVACHI ##############
CREATE TABLE IF NOT EXISTS cat_thiruvachi (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(225) NOT NULL,
  leg_breadth INT NOT NULL,
  sheet_thick INT NOT NULL,
  work_type ENUM('Regular', 'Customized') NOT NULL DEFAULT 'Regular',
  work_details TEXT NULL,
  cost INT NOT NULL
);

CREATE TABLE IF NOT EXISTS cat_thiruvachi_rates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  gold_rate INT NOT NULL DEFAULT 0, 
  silver_rate INT NOT NULL DEFAULT 0,
  pure_silver_rate INT NOT NULL DEFAULT 0,
  pure_silver_margin_rate INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cat_thiruvachi_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cat_thiruvachi_id INT NOT NULL,
  img LONGBLOB NOT NULL,
  img_type VARCHAR(50) NOT NULL,
  is_primary TINYINT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (cat_thiruvachi_id)
    REFERENCES cat_thiruvachi(id)
    ON DELETE CASCADE
);


-- ############## KAVASAM ##############
CREATE TABLE IF NOT EXISTS cat_kavasam (
  id INT AUTO_INCREMENT PRIMARY KEY,
  SQFT INT UNIQUE NOT NULL, 
  gauge_24 INT NOT NULL DEFAULT 0, 
  gauge_22 INT NOT NULL DEFAULT 0, 
  gauge_20 INT NOT NULL DEFAULT 0, 
  wax_cost INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cat_kavasam_rates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  gold_rate INT NOT NULL DEFAULT 0, 
  silver_rate INT NOT NULL DEFAULT 0,
  pure_silver_rate INT NOT NULL DEFAULT 0,
  pure_silver_margin_rate INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cat_kavasam_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  img LONGBLOB NOT NULL,
  img_type VARCHAR(50) NOT NULL,
  is_primary TINYINT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ############## VAHANAM ##############
CREATE TABLE IF NOT EXISTS cat_vahanam (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(225) NULL,
  specification VARCHAR(1000) NULL,

  wood_hgt_1_5ft INT NOT NULL DEFAULT 0,
  wood_hgt_2ft INT NOT NULL DEFAULT 0,
  wood_hgt_2_5ft INT NOT NULL DEFAULT 0,
  wood_hgt_3ft INT NOT NULL DEFAULT 0,
  wood_hgt_3_5ft INT NOT NULL DEFAULT 0,
  wood_hgt_4ft INT NOT NULL DEFAULT 0,
  wood_hgt_5ft INT NOT NULL DEFAULT 0,

  brass_hgt_1_5ft INT NOT NULL DEFAULT 0,
  brass_hgt_2ft INT NOT NULL DEFAULT 0,
  brass_hgt_2_5ft INT NOT NULL DEFAULT 0,
  brass_hgt_3ft INT NOT NULL DEFAULT 0,
  brass_hgt_3_5ft INT NOT NULL DEFAULT 0,
  brass_hgt_4ft INT NOT NULL DEFAULT 0,
  brass_hgt_5ft INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cat_vahanam_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cat_vahanam_id INT NOT NULL,
  img LONGBLOB NOT NULL,
  img_type VARCHAR(50) NOT NULL,
  is_primary TINYINT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (cat_vahanam_id)
    REFERENCES cat_vahanam(id)
    ON DELETE CASCADE
);


-- ############## SHEET METAL ##############
CREATE TABLE IF NOT EXISTS cat_sheet_metal (
  id INT AUTO_INCREMENT PRIMARY KEY,
  heads VARCHAR(225) NOT NULL,
  work_desc VARCHAR(1000) NULL,
  gauge_20__below_21_SQFT INT NOT NULL DEFAULT 0,
  gauge_20__21_50_SQFT INT NOT NULL DEFAULT 0, 
  gauge_20__above_50_SQFT INT NOT NULL DEFAULT 0, 
  gauge_22__below_21_SQFT INT NOT NULL DEFAULT 0, 
  gauge_22__21_50_SQFT INT NOT NULL DEFAULT 0, 
  gauge_22__above_50_SQFT INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cat_sheet_metal_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  img LONGBLOB NOT NULL,
  img_type VARCHAR(50) NOT NULL,
  is_primary TINYINT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ############## PANCHALOHA STATUE ##############
CREATE TABLE IF NOT EXISTS cat_panchaloha_statue (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(225) NOT NULL,
  prabavali ENUM('Yes', 'No') NOT NULL DEFAULT 'No',
  position VARCHAR(1000) NOT NULL,
  model VARCHAR(1000) NOT NULL,
  hands INT NOT NULL DEFAULT 0,
  height DECIMAL(5,1) NOT NULL DEFAULT 0,
  weight DECIMAL(6,1) NOT NULL DEFAULT 0,
  cost INT NOT NULL DEFAULT 0
);


CREATE TABLE IF NOT EXISTS cat_panchaloha_statue_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cat_panchaloha_statue_id INT NOT NULL,
  img LONGBLOB NOT NULL,
  img_type VARCHAR(50) NOT NULL,
  is_primary TINYINT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (cat_panchaloha_statue_id)
    REFERENCES cat_panchaloha_statue(id)
    ON DELETE CASCADE
);


-- ############## KODIMARAM ##############
CREATE TABLE IF NOT EXISTS cat_kodimaram_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  img LONGBLOB NOT NULL,
  img_type VARCHAR(50) NOT NULL,
  is_primary TINYINT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- ########################################################
-- ############### CATEGORY TABLE INSERTION ###############
-- ########################################################

-- ################# THIRUVACHI #################
INSERT INTO cat_thiruvachi (
  name,
  leg_breadth,
  sheet_thick,
  work_type,
  work_details,
  cost
  )
VALUES
  ('RGL 26 gauge', 6, 26, 'Regular', 'Rgl', 1764),
  ('RGl 22 Gauge', 6, 22, 'Regular', 'Rgl', 3234),
  ('22 gauge Mid Spl', 7, 22, 'Regular', 'Rgl design', 3950),
  ('22 gauge Spl', 8, 22, 'Customized', 'Rgl design with  Spl 3', 4730),
  ('22 gauge Spl', 10, 22, 'Customized', 'Customzed design-drawing to be provided to the customer-after approval we manufactruar', 6160),
  ('22 gauge', 10, 22, 'Customized', 'Customzed design-wit h cut out model drawing to be provided to the customer-after approval we manufactruar', 6930),
  ('22 gauge', 12, 20, 'Customized', 'Customzed designl drawing to be provided to the customer-after approval we manufactruar 3 d model', 10395);

-- Insert into Thiruvachi Rates table
INSERT INTO cat_thiruvachi_rates (
    gold_rate,
    silver_rate,
    pure_silver_rate,
    pure_silver_margin_rate
)
VALUES
    (11000, 3500, 254, 46);



-- ################# KAVASAM #################
INSERT INTO cat_kavasam (
    SQFT,
    gauge_20,
    gauge_22,
    gauge_24,
    wax_cost
)
VALUES
  (1, 7350, 6300, 5250, 1500),
  (2, 6825, 5775, 4725, 1500),
  (3, 6825, 5775, 4725, 1500),
  (4, 6300, 5250, 4200, 2000),
  (5, 6300, 5250, 4200, 2000),
  (6, 6300, 5250, 4200, 2000),
  (7, 6300, 5250, 4200, 2000),
  (8, 6300, 5250, 4200, 2000),
  (9, 5775, 4725, 3938, 4000),
  (10, 5775, 4725, 3938, 4000),
  (11, 5775, 4725, 3938, 4000),
  (12, 5775, 4725, 3938, 5000),
  (13, 5775, 4725, 3938, 5000),
  (14, 5775, 4725, 3938, 5000),
  (15, 5775, 4725, 3938, 5000);


-- Insert into Kavasam Rates table
INSERT INTO cat_kavasam_rates (
    gold_rate,
    silver_rate,
    pure_silver_rate,
    pure_silver_margin_rate
)
VALUES
    (11000, 3500, 254, 46);



-- ################# SHEET METAL #################
INSERT INTO cat_sheet_metal (
            heads,
            work_desc,
            gauge_20__below_21_SQFT,
            gauge_20__21_50_SQFT,
            gauge_20__above_50_SQFT,
            gauge_22__below_21_SQFT,
            gauge_22__21_50_SQFT,
            gauge_22__above_50_SQFT
)
VALUES
    (
        'Nilai Padi Plain',
        'Drawing to be provided to the customer and get approval; after that, plan to make as per the drawing.',
        3450, 3162.5, 2875, 2990, 2760, 2530
    ),
    (
        'Nilai Padi Vargam',
        'Drawing to be provided to the customer and get approval; after that, plan to make as per the drawing.',
        4025, 3450, 3162.5, 3565, 2990, 2760
    ),
    (
        'Additional Customized Picture',
        'Drawing to be provided to the customer and get approval; after that, plan to make as per the drawing.',
        2300, 2300, 2300, 2300, 2300, 2300
    );



-- ################# VAHANAM #################
INSERT INTO cat_vahanam (
    name,
    specification,
    wood_hgt_1_5ft,
    wood_hgt_2ft,
    wood_hgt_2_5ft,
    wood_hgt_3ft,
    wood_hgt_3_5ft,
    wood_hgt_4ft,
    wood_hgt_5ft,
    brass_hgt_1_5ft,
    brass_hgt_2ft,
    brass_hgt_2_5ft,
    brass_hgt_3ft,
    brass_hgt_3_5ft,
    brass_hgt_4ft,
    brass_hgt_5ft
)
VALUES
    ('RISHABAM',	'Standing -with Based beedam and Swany sitting stand',	32000,	48000,	72000,	88000,	123200,	172480,	241472, 0, 0, 0, 0, 0, 0, 0),
    ('Simmam',	'Standing -with Based beedam and Swany sitting stand',	32000,	48000,	72000,	88000,	123200,	172480,	241472, 0, 0, 0, 0, 0, 0, 0),
    ('Horse',	'Standing -with Based beedam and Swany sitting stand',	32000,	48000,	72000,	88000,	123200,	172480,	241472, 0, 0, 0, 0, 0, 0, 0),
    ('Munchur',	'Standing -with Based beedam and Swany sitting stand',	32000,	48000,	72000,	88000,	123200,	172480,	241472, 0, 0, 0, 0, 0, 0, 0),
    ('Garudan',	'Standing -with Based beedam and Swany sitting stand',	32000,	48000,	72000,	88000,	123200,	172480,	241472, 0, 0, 0, 0, 0, 0, 0),
    ('Hanuman',	'Standing -with Based beedam and Swany sitting stand',	32000,	48000,	72000,	88000,	123200,	172480,	241472, 0, 0, 0, 0, 0, 0, 0),
    ('Suran',	'Standing -with Based beedam-3 faces Detachable',	38400,	57600,	86400,	105600,	147840,	206976,	289766.4, 0, 0, 0, 0, 0, 0, 0),
    ('Goat',	'Standing -with Based beedam and Swany sitting stand',	32000,	48000,	72000,	88000,	123200,	172480,	241472, 0, 0, 0, 0, 0, 0, 0),
    ('Puli ',	'Standing -with Based beedam and Swany sitting stand',	32000,	48000,	72000,	88000,	123200,	172480,	241472, 0, 0, 0, 0, 0, 0, 0),
    ('Elephant',	'Standing -with Based beedam and Swany sitting stand',	44800,	62400,	93600,	114400,	160160,	224224,	313913.6, 0, 0, 0, 0, 0, 0, 0),
    ('Annam',	'Standing -with Based beedam and Swany sitting stand',	41600,	64800,	97200,	118800,	166320,	232848,	325987.2, 0, 0, 0, 0, 0, 0, 0),
    ('Peacock',	'Standing -with Based beedam and Swany sitting stand',	41600,	64800,	97200,	118800,	166320,	232848,	325987.2, 0, 0, 0, 0, 0, 0, 0),
    ('Snake ',	'Five face head--base beedam',	44800,	62400,	93600,	114400,	160160,	224224,	313913.6, 0, 0, 0, 0, 0, 0, 0),
    ('Suriya Brabai',	'Suriyan base  with Arch-with Beedam-with 7 horse and Choriater',	49920,	77760,	116640,	142560,	199584,	279417.6,	391184.64, 0, 0, 0, 0, 0, 0, 0),
    ('Chndra Brabai',	'Chandran  base  with Arch-with Beedam',	32000,	48000,	72000,	88000,	123200,	172480,	241472, 0, 0, 0, 0, 0, 0, 0);


-- ################# PANCHALOHA STATUE #################
INSERT INTO cat_panchaloha_statue (
  name,
  prabavali,
  position,
  model,
  hands,
  height,
  weight,
  cost
)
VALUES
  ('Vinaygar',	'No',	'Standing',	'Valampuri/Eadampuri',	'4',	'18',	'25',	'63000'),
  ('Vinaygar',	'No',	'Standing',	'Valampuri/Eadampuri',	'4',	'21',	'38',	'95760'),
  ('Vinaygar',	'No',	'Standing',	'Valampuri/Eadampuri',	'4',	'24',	'48',	'120960'),
  ('Vinaygar',	'No',	'Standing',	'Valampuri/Eadampuri',	'4',	'27',	'60',	'151200'),
  ('Vinaygar',	'No',	'Standing',	'Valampuri/Eadampuri',	'4',	'30',	'80',	'201600'),
  ('Vinaygar',	'Yes',	'Sitting with Thiruvatchi',	'Valampuri/Eadampuri',	'4',	'18',	'30',	'75600'),
  ('Vinaygar',	'Yes',	'Sitting with Thiruvatchi',	'Valampuri/Eadampuri',	'4',	'21',	'45',	'113400'),
  ('Vinaygar',	'Yes',	'Sitting with Thiruvatchi',	'Valampuri/Eadampuri',	'4',	'24',	'60',	'151200'),
  ('Vinaygar',	'Yes',	'Sitting with Thiruvatchi',	'Valampuri/Eadampuri',	'4',	'27',	'77',	'194040'),
  ('Vinaygar',	'Yes',	'Sitting with Thiruvatchi',	'Valampuri/Eadampuri',	'4',	'30',	'99',	'249480'),
  ('Mariyamman All',	'Yes',	'Sitting with Thiruvatchi',	'With Nagam/Sudar ',	'4',	'18',	'25',	'63000'),
  ('Mariyamman All',	'Yes',	'Sitting with Thiruvatchi',	'With Nagam/Sudar ',	'4',	'21',	'36',	'90720'),
  ('Mariyamman All',	'Yes',	'Sitting with Thiruvatchi',	'With Nagam/Sudar ',	'4',	'24',	'45',	'113400'),
  ('Mariyamman All',	'Yes',	'Sitting with Thiruvatchi',	'With Nagam/Sudar ',	'4',	'27',	'55',	'138600'),
  ('Mariyamman All',	'Yes',	'Sitting with Thiruvatchi',	'With Nagam/Sudar ',	'4',	'30',	'70',	'176400'),
  ('Mariyamman All',	'No',	'Sitting with out Thiruvatchi',	'With Nagam/Sudar ',	'4',	'18',	'32',	'80640'),
  ('Mariyamman All',	'No',	'Sitting with out Thiruvatchi',	'With Nagam/Sudar ',	'4',	'21',	'46',	'115920'),
  ('Mariyamman All',	'No',	'Sitting with out Thiruvatchi',	'With Nagam/Sudar ',	'4',	'24',	'55',	'138600'),
  ('Mariyamman All',	'No',	'Sitting with out Thiruvatchi',	'With Nagam/Sudar ',	'4',	'27',	'70',	'176400'),
  ('Mariyamman All',	'No',	'Sitting with out Thiruvatchi',	'With Nagam/Sudar ',	'4',	'30',	'90',	'226800'),
  ('Mariyamman All Standing',	'No',	'without Thiruvatchi',	'With Nagam/Sudar ',	'4',	'18',	'16',	'40320'),
  ('Mariyamman All Standing',	'No',	'without Thiruvatchi',	'With Nagam/Sudar ',	'4',	'21',	'22',	'55440'),
  ('Mariyamman All Standing',	'No',	'without Thiruvatchi',	'With Nagam/Sudar ',	'4',	'24',	'30',	'75600'),
  ('Mariyamman All Standing',	'No',	'without Thiruvatchi',	'With Nagam/Sudar ',	'4',	'27',	'38',	'95760'),
  ('Mariyamman All Standing',	'No',	'without Thiruvatchi',	'With Nagam/Sudar ',	'4',	'30',	'50',	'126000'),
  ('Perumal /Visnu',	'No',	'Standing ',	'Avayam vartaham/Uthuvasthu Model',	'4',	'18',	'15',	'42525'),
  ('Perumal /Visnu',	'No',	'Standing ',	'Avayam vartaham/Uthuvasthu Model',	'4',	'21',	'22',	'62370'),
  ('Perumal /Visnu',	'No',	'Standing ',	'Avayam vartaham/Uthuvasthu Model',	'4',	'24',	'30',	'85050'),
  ('Perumal /Visnu',	'No',	'Standing ',	'Avayam vartaham/Uthuvasthu Model',	'4',	'27',	'38',	'107730'),
  ('Perumal /Visnu',	'No',	'Standing ',	'Avayam vartaham/Uthuvasthu Model',	'4',	'30',	'50',	'141750'),
  ('Perumal Set',	'No',	'Standing',	'Avayam vartaham/Uthuvasthu Model',	'4',	'18',	'28',	'74970'),
  ('Perumal Set',	'No',	'Standing',	'Avayam vartaham/Uthuvasthu Model',	'4',	'21',	'40',	'107100'),
  ('Perumal Set',	'No',	'Standing',	'Avayam vartaham/Uthuvasthu Model',	'4',	'24',	'55',	'147262.5'),
  ('Perumal Set',	'No',	'Standing',	'Avayam vartaham/Uthuvasthu Model',	'4',	'27',	'70',	'187425'),
  ('Perumal Set',	'No',	'Standing',	'Avayam vartaham/Uthuvasthu Model',	'4',	'30',	'90',	'240975'),
  ('Ramar Set',	'No',	'Standing',	'All 3 god Is stanting separate Pieces-hanuman only Sitting',	'2',	'18',	'32',	'85680'),
  ('Ramar Set',	'No',	'Standing',	'All 3 god Is stanting separate Pieces-hanuman only Sitting',	'2',	'21',	'45',	'120487.5'),
  ('Ramar Set',	'No',	'Standing',	'All 3 god Is stanting separate Pieces-hanuman only Sitting',	'2',	'24',	'62',	'166005'),
  ('Ramar Set',	'No',	'Standing',	'All 3 god Is stanting separate Pieces-hanuman only Sitting',	'2',	'27',	'80',	'214200'),
  ('Ramar Set',	'No',	'Standing',	'All 3 god Is stanting separate Pieces-hanuman only Sitting',	'2',	'30',	'95',	'254362.5'),
  ('Krisnara Set',	'No',	'Standing',	'All 3 god separaete pieces-Krisnara with Pulamkulal',	'2',	'18',	'32',	'85680'),
  ('Krisnara Set',	'No',	'Standing',	'All 3 god separaete pieces-Krisnara with Pulamkulal',	'2',	'21',	'45',	'120487.5'),
  ('Krisnara Set',	'No',	'Standing',	'All 3 god separaete pieces-Krisnara with Pulamkulal',	'2',	'24',	'62',	'166005'),
  ('Siven Set',	'No',	'Standing',	'All 2 god is Seperated',	'4',	'18',	'21',	'56227.5'),
  ('Siven Set',	'No',	'Standing',	'All 2 god is Seperated',	'4',	'21',	'31',	'83002.5'),
  ('Siven Set',	'No',	'Standing',	'All 2 god is Seperated',	'4',	'24',	'42',	'112455'),
  ('Siven Set',	'No',	'Standing',	'All 2 god is Seperated',	'4',	'27',	'55',	'147262.5'),
  ('Siven Set',	'No',	'Standing',	'All 2 god is Seperated',	'4',	'30',	'70',	'187425'),
  ('Siven Set',	'Yes',	'Standing',	'with thiruvatchi all in one beedam',	'2',	'18',	'22',	'62370'),
  ('Siven Set',	'Yes',	'Standing',	'with thiruvatchi all in one beedam',	'2',	'21',	'35',	'99225'),
  ('Siven Set',	'Yes',	'Standing',	'with thiruvatchi all in one beedam',	'2',	'24',	'50',	'141750'),
  ('Siven Set',	'Yes',	'Standing',	'with thiruvatchi all in one beedam',	'2',	'27',	'60',	'170100'),
  ('Siven Set',	'Yes',	'Standing',	'with thiruvatchi all in one beedam',	'2',	'30',	'80',	'226800'),
  ('Prodhosa moorthi',	'Yes',	'Sitting with Cow',	'with thiruvatchi sitted in Cow',	'4',	'18',	'25',	'66937.5'),
  ('Prodhosa moorthi',	'Yes',	'Sitting with Cow',	'with thiruvatchi sitted in Cow',	'4',	'21',	'40',	'107100'),
  ('Prodhosa moorthi',	'Yes',	'Sitting with Cow',	'with thiruvatchi sitted in Cow',	'4',	'24',	'55',	'147262.5'),
  ('Subramanayar Set',	'No',	'Stanting',	'All 3 god is standing with vel sevel kodi',	'4',	'18',	'30',	'80325'),
  ('Subramanayar Set',	'No',	'Stanting',	'All 3 god is standing with vel sevel kodi',	'4',	'21',	'44',	'117810'),
  ('Subramanayar Set',	'No',	'Stanting',	'All 3 god is standing with vel sevel kodi',	'4',	'24',	'60',	'160650'),
  ('Subramanayar Set',	'No',	'Stanting',	'All 3 god is standing with vel sevel kodi',	'4',	'27',	'75',	'200812.5'),
  ('Subramanayar Set',	'No',	'Stanting',	'All 3 god is standing with vel sevel kodi',	'4',	'30',	'98',	'262395'),
  ('Murugar only',	'No',	'Standing',	'Single vel/sevelkodi with Mayil',	'4',	'18',	'16',	'45360'),
  ('Murugar only',	'No',	'Standing',	'Single vel/sevelkodi with Mayil',	'4',	'21',	'22',	'62370'),
  ('Murugar only',	'No',	'Standing',	'Single vel/sevelkodi with Mayil',	'4',	'24',	'30',	'85050'),
  ('Murugar only',	'No',	'Standing',	'Single vel/sevelkodi with Mayil',	'4',	'27',	'38',	'107730'),
  ('Murugar only',	'No',	'Standing',	'Single vel/sevelkodi with Mayil',	'4',	'30',	'50',	'141750'),
  ('Bala Murugar',	'No',	'Standing',	'Single piece with mayil with Vel',	'2',	'18',	'18',	'51030'),
  ('Bala Murugar',	'No',	'Standing',	'Single piece with mayil with Vel',	'2',	'21',	'26',	'73710'),
  ('Bala Murugar',	'No',	'Standing',	'Single piece with mayil with Vel',	'2',	'24',	'35',	'99225'),
  ('Bala Murugar',	'No',	'Standing',	'Single piece with mayil with Vel',	'2',	'27',	'45',	'127575'),
  ('Bala Murugar',	'No',	'Standing',	'Single piece with mayil with Vel',	'2',	'30',	'60',	'170100'),
  ('Hanuman ',	'No',	'Standing',	'Asiwatham/Baktha anjenayar',	'2',	'18',	'20',	'56700'),
  ('Hanuman ',	'No',	'Standing',	'Asiwatham/Baktha anjenayar',	'2',	'21',	'29',	'82215'),
  ('Hanuman ',	'No',	'Standing',	'Asiwatham/Baktha anjenayar',	'2',	'24',	'39',	'110565'),
  ('Hanuman ',	'No',	'Standing',	'Asiwatham/Baktha anjenayar',	'2',	'27',	'50',	'141750'),
  ('Hanuman ',	'No',	'Standing',	'Asiwatham/Baktha anjenayar',	'2',	'30',	'66',	'187110'),
  ('Nadarajar',	'No',	'Standing ',	'With Arch -single round',	'4',	'18',	'12',	'37800'),
  ('Nadarajar',	'No',	'Standing ',	'With Arch -single round',	'4',	'21',	'20',	'63000'),
  ('Nadarajar',	'No',	'Standing ',	'With Arch -single round',	'4',	'24',	'26',	'81900'),
  ('Nadarajar',	'No',	'Standing ',	'With Arch -single round',	'4',	'27',	'30',	'94500'),
  ('Nadarajar',	'No',	'Standing ',	'With Arch -single round',	'4',	'30',	'40',	'126000'),
  ('Nadarajar',	'No',	'Standing ',	'With Arch -single round',	'4',	'36',	'55',	'173250'),
  ('Sivagami ',	'No',	'Stanidng',	'Single',	'2',	'12',	'3',	'9450'),
  ('Sivagami ',	'No',	'Stanidng',	'Single',	'2',	'15',	'5',	'15750'),
  ('Sivagami ',	'No',	'Stanidng',	'Single',	'2',	'18',	'8',	'25200'),
  ('Sivagami ',	'No',	'Stanidng',	'Single',	'2',	'21',	'10',	'31500'),
  ('Sivagami ',	'No',	'Stanidng',	'Single',	'2',	'24',	'12',	'37800'),
  ('Ayappan',	'Yes',	'Sitting ',	'with Thiruvatchi ',	'2',	'18',	'22',	'55440'),
  ('Ayappan',	'Yes',	'Sitting ',	'with Thiruvatchi ',	'2',	'21',	'32',	'80640'),
  ('Ayappan',	'Yes',	'Sitting ',	'with Thiruvatchi ',	'2',	'24',	'45',	'113400'),
  ('Ayappan',	'Yes',	'Sitting ',	'with Thiruvatchi ',	'2',	'27',	'55',	'138600'),
  ('Ayappan',	'Yes',	'Sitting ',	'with Thiruvatchi ',	'2',	'30',	'75',	'189000'),
  ('Laskshmi/Kamatchi/Rajaewari/lalithambigai/Saraswathi',	'Yes',	'Sitting ',	'With Thiruvatchi',	'4',	'18',	'26',	'69615'),
  ('Laskshmi/Kamatchi/Rajaewari/lalithambigai/Saraswathi',	'Yes',	'Sitting ',	'With Thiruvatchi',	'4',	'21',	'40',	'107100'),
  ('Laskshmi/Kamatchi/Rajaewari/lalithambigai/Saraswathi',	'Yes',	'Sitting ',	'With Thiruvatchi',	'4',	'24',	'55',	'147262.5'),
  ('Laskshmi/Kamatchi/Rajaewari/lalithambigai/Saraswathi',	'Yes',	'Sitting ',	'With Thiruvatchi',	'4',	'27',	'70',	'187425'),
  ('Laskshmi/Kamatchi/Rajaewari/lalithambigai/Saraswathi',	'Yes',	'Sitting ',	'With Thiruvatchi',	'4',	'30',	'90',	'240975'),
  ('Laskshmi/Kamatchi/Rajaewari/lalithambigai/Saraswathi',	'No',	'Sitting ',	'With out Thiruvatchi',	'4',	'18',	'32',	'85680'),
  ('Laskshmi/Kamatchi/Rajaewari/lalithambigai/Saraswathi',	'No',	'Sitting ',	'With out Thiruvatchi',	'4',	'21',	'48',	'128520'),
  ('Laskshmi/Kamatchi/Rajaewari/lalithambigai/Saraswathi',	'No',	'Sitting ',	'With out Thiruvatchi',	'4',	'24',	'60',	'160650'),
  ('Laskshmi/Kamatchi/Rajaewari/lalithambigai/Saraswathi',	'No',	'Sitting ',	'With out Thiruvatchi',	'4',	'27',	'80',	'214200'),
  ('Laskshmi/Kamatchi/Rajaewari/lalithambigai/Saraswathi',	'No',	'Sitting ',	'With out Thiruvatchi',	'4',	'30',	'98',	'262395');
