
-- We start by creating a regular SQL table

SET TIME ZONE 'UTC';

DROP TABLE IF EXISTS portal_activity;
CREATE TABLE portal_activity (
  time        TIMESTAMPTZ       NOT NULL,
  datasetid    varchar(250),
  name varchar(250),
  created_at timestamp,
  updated_at timestamp,
  pub_dept varchar(250), 
  pub_freq varchar(250),
  pub_health varchar(100),
  days_last_updt varchar(100)
);

UPDATE  portal_activity
   SET time = time AT TIME ZONE 'UTC';

-- This creates a hypertable that is partitioned by time
--   using the values in the `time` column.
SELECT create_hypertable('portal_activity', 'time');
-- see this for more info: http://docs.timescale.com/latest/api/api-timescaledb#create_hypertable-best-practices
-- timescaledb divides dat into time chunks. This makes performance better; by dividing into chunks it
-- feels like a continuous table but its chunks

SELECT set_chunk_time_interval('portal_activity', 604800000000);
-- set the chunk interval to a week- means we are dividing the hypertable into week long chunks
-- we will use this when we delete  old data out of the portal activity table ot prevent it from getting too big
--drop_chunks()
-- Removes data chunks that are older than a given time interval across all hypertables or a specific one. Chunks are removed only if ​all​ of their data is beyond the cut-off point, so the remaining data may contain timestamps that are before the cut-off point, but only one chunk's worth.
-- SELECT drop_chunks(interval '2 weeks', 'portal_activity');



DROP TABLE IF EXISTS deleted_datasets;
CREATE TABLE deleted_datasets(
	time        TIMESTAMPTZ       NOT NULL,
	datasetid    varchar(250),
	name 		varchar(250),
	last_seen  TIMESTAMPTZ NOT NULL,
	pub_dept   varchar(250), 
 	pub_freq varchar(250),
 	updated_at timestamp, 
 	created_at timestamp, 
 	notification boolean
);
UPDATE  deleted_datasets
   SET time = time AT TIME ZONE 'UTC';

UPDATE  deleted_datasets
   SET last_seen = last_seen  AT TIME ZONE 'UTC';


SELECT create_hypertable('deleted_datasets', 'time');
#ALTER TABLE deleted_datasets ALTER last_seen TYPE timestamptz USING last_seen AT TIME ZONE '';


DROP TABLE IF EXISTS created_datasets;
CREATE TABLE created_datasets(
	time        TIMESTAMPTZ       NOT NULL,
	datasetid    varchar(250),
	name 		varchar(250),
	first_seen  TIMESTAMPTZ       NOT NULL,
  created_at timestamp, 
	pub_dept   varchar(250), 
 	pub_freq varchar(250),
 	deleted_last_seen TIMESTAMPTZ , 
  time_btw_deleted_and_first_seen INTERVAL , 
 	notification boolean
);

UPDATE  created_datasets
   SET time = time  AT TIME ZONE 'UTC';
UPDATE  created_datasets
   SET first_seen = first_seen  AT TIME ZONE 'UTC';
UPDATE  created_datasets
   SET deleted_last_seen = deleted_last_seen  AT TIME ZONE 'UTC';
SELECT create_hypertable('created_datasets', 'time');



DROP TABLE IF EXISTS late_updated_datasets;
CREATE TABLE late_updated_datasets(
	time        TIMESTAMPTZ       NOT NULL,
	datasetid    varchar(250),
	name 		varchar(250),
  last_checked TIMESTAMPTZ NOT NULL,
  pub_health varchar(100),
	updated_at   timestamp,    
  pub_freq varchar(250),
  days_last_updt varchar(100),
	pub_dept   varchar(250), 
  created_at timestamp, 
 	notification boolean
);

UPDATE  late_updated_datasets
   SET time = time  AT TIME ZONE 'UTC';
UPDATE  late_updated_datasets
   SET last_checked = last_checked  AT TIME ZONE 'UTC';

SELECT create_hypertable('late_updated_datasets', 'time');






