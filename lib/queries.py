#####################################################################################
# EXCLUDED COHORT IDs
# Defined once here — used in all home queries below.
# To add/remove an exclusion, edit this list only.
#####################################################################################

_EXCLUDED_COHORT_IDS = "(184, 137, 149, 152, 18, 194, 19, 161, 182, 174, 140, 220, 222)"


#####################################################################################
# HOME PAGE QUERIES
#####################################################################################

# Resolves patients with multiple demographic rows by picking one row per patient,
# prioritising RADAR-sourced records over UKRDC. This ensures male + female = total.
SQL_REGISTRY_OVERVIEW = """
WITH patient_gender_resolution AS (
    SELECT DISTINCT ON (gp.patient_id)
        gp.patient_id,
        pd.gender
    FROM group_patients gp
    JOIN patient_demographics pd ON pd.patient_id = gp.patient_id
    WHERE gp.group_id = 123
    ORDER BY gp.patient_id,
        CASE WHEN pd.source_type = 'RADAR' THEN 1 ELSE 2 END
)
SELECT
    COUNT(DISTINCT patient_id)                                        AS total_patients,
    COUNT(DISTINCT patient_id) FILTER (WHERE gender = 1)             AS male_count,
    COUNT(DISTINCT patient_id) FILTER (WHERE gender = 2)             AS female_count,
    COUNT(DISTINCT patient_id) FILTER (WHERE gender NOT IN (1, 2)
                                        OR gender IS NULL)            AS unknown_gender
FROM patient_gender_resolution;
"""


# COUNT(id) instead of COUNT(name) so NULL names are still counted
SQL_TOTAL_COHORTS = f"""
SELECT COUNT(id) AS total_cohorts
FROM groups
WHERE type = 'COHORT'
AND id NOT IN {_EXCLUDED_COHORT_IDS};
"""


SQL_HOME_COHORT_STRUCTURE = f"""
SELECT
    g.id,
    g.name,
    COUNT(DISTINCT gp.patient_id) AS total_patients,
    COUNT(DISTINCT gp.patient_id) FILTER (
        WHERE pd.date_of_birth IS NOT NULL
          AND EXTRACT(YEAR FROM AGE(CURRENT_DATE, pd.date_of_birth)) < 18
    ) AS child_count,
    COUNT(DISTINCT gp.patient_id) FILTER (
        WHERE pd.date_of_birth IS NOT NULL
          AND EXTRACT(YEAR FROM AGE(CURRENT_DATE, pd.date_of_birth)) >= 18
    ) AS adult_count,
    COUNT(DISTINCT gp.patient_id) FILTER (
        WHERE pd.date_of_birth IS NULL
    ) AS unknown_age_count
FROM group_patients gp
JOIN groups g ON gp.group_id = g.id
JOIN patient_demographics pd ON gp.patient_id = pd.patient_id
WHERE g.type = 'COHORT'
  AND g.id NOT IN {_EXCLUDED_COHORT_IDS}
GROUP BY g.id, g.name
ORDER BY g.id;
"""


#####################################################################################
# KIDNEY FAILURE EVENTS QUERIES
#####################################################################################

EGFR_OBS_ID = 47  # observation_id for eGFR readings in the results table

SQL_KF_COHORTS = f"""
SELECT g.id, g.name,
       COUNT(DISTINCT gp.patient_id) AS patient_count
FROM groups g
JOIN group_patients gp ON g.id = gp.group_id
WHERE g.type = 'COHORT'
  AND g.id NOT IN {_EXCLUDED_COHORT_IDS}
GROUP BY g.id, g.name
ORDER BY g.name;
"""

SQL_KIDNEY_FAILURE_EVENTS = """
WITH cohort_patients AS (
    SELECT DISTINCT patient_id
    FROM group_patients
    WHERE group_id = %(cohort_id)s
),
transplant_events AS (
    SELECT patient_id, MIN(date) AS transplant_date
    FROM transplants
    WHERE patient_id IN (SELECT patient_id FROM cohort_patients)
    GROUP BY patient_id
),
dialysis_events AS (
    SELECT patient_id, MIN(from_date) AS dialysis_date
    FROM dialysis
    WHERE patient_id IN (SELECT patient_id FROM cohort_patients)
    GROUP BY patient_id
),
egfr_low AS (
    SELECT
        r.patient_id,
        r.date::date                   AS observation_date,
        NULLIF(r.value, '')::numeric   AS egfr_value
    FROM results r
    WHERE r.patient_id IN (SELECT patient_id FROM cohort_patients)
      AND r.observation_id = %(egfr_obs_id)s
      AND NULLIF(r.value, '')::numeric < 15
),
egfr_pairs AS (
    SELECT
        a.patient_id,
        a.observation_date             AS first_date,
        a.egfr_value                   AS first_value,
        b.observation_date             AS second_date,
        b.egfr_value                   AS second_value,
        (b.observation_date - a.observation_date) AS days_between
    FROM egfr_low a
    JOIN egfr_low b
      ON a.patient_id = b.patient_id
     AND b.observation_date > a.observation_date
    WHERE (b.observation_date - a.observation_date) >= 28
      AND NOT EXISTS (
          SELECT 1 FROM results o
          WHERE o.patient_id     = a.patient_id
            AND o.observation_id = %(egfr_obs_id)s
            AND NULLIF(o.value, '')::numeric >= 15
            AND o.date::date > a.observation_date
            AND o.date::date < b.observation_date
      )
),
egfr_events AS (
    SELECT DISTINCT ON (patient_id)
        patient_id,
        first_date, first_value,
        second_date, second_value,
        days_between,
        'eGFR <15 x2' AS rule
    FROM egfr_pairs
    ORDER BY patient_id, first_date
),
all_events AS (
    SELECT patient_id, transplant_date AS event_date, 'Transplant'  AS rule FROM transplant_events
    UNION ALL
    SELECT patient_id, dialysis_date   AS event_date, 'Dialysis'    AS rule FROM dialysis_events
    UNION ALL
    SELECT patient_id, second_date     AS event_date, 'eGFR <15 x2' AS rule FROM egfr_events
)
SELECT
    cp.patient_id,
    ae.event_date,
    ae.rule,
    t.transplant_date,
    d.dialysis_date,
    ee.first_value   AS egfr_first_value,
    ee.first_date    AS egfr_first_date,
    ee.second_value  AS egfr_second_value,
    ee.second_date   AS egfr_second_date,
    ee.days_between  AS egfr_days_between
FROM cohort_patients cp
LEFT JOIN all_events ae       ON cp.patient_id = ae.patient_id
LEFT JOIN transplant_events t ON cp.patient_id = t.patient_id
LEFT JOIN dialysis_events d   ON cp.patient_id = d.patient_id
LEFT JOIN egfr_events ee      ON cp.patient_id = ee.patient_id
WHERE ae.patient_id IS NOT NULL
ORDER BY cp.patient_id, ae.event_date;
"""


#####################################################################################
# BIOPSY PAGE QUERIES
#####################################################################################

SQL_BIOPSY_MISSING = """
WITH hospital_ranked AS (
  SELECT
      pd.patient_id,
      pd.from_date::date                                              AS diagnosed_date,
      pd.created_date::date                                           AS recruited_date,
      pdemo.date_of_birth,
      EXTRACT(YEAR FROM AGE(CURRENT_DATE, pdemo.date_of_birth))::int  AS age,
      gr.name                                                         AS hospital_name,
      gr.code                                                         AS hospital_code,
      ROW_NUMBER() OVER (
        PARTITION BY pd.patient_id
        ORDER BY gp.from_date DESC NULLS LAST, pd.created_date DESC, gp.id ASC
      ) AS rn
  FROM patient_diagnoses pd
  JOIN patients p                  ON p.id = pd.patient_id
  JOIN patient_demographics pdemo  ON pdemo.patient_id = pd.patient_id
  JOIN group_patients gp           ON gp.patient_id = pd.patient_id
  JOIN groups gr                   ON gr.id = gp.group_id
  WHERE pd.biopsy IS TRUE
    AND gr.type = 'HOSPITAL'
    AND pd.patient_id NOT IN (
        SELECT id FROM patients WHERE test = TRUE OR control = TRUE
    )

    -- NATIVE-ELIGIBLE: patient must have at least one NATIVE pathology row,
    -- OR have zero pathology rows at all (never uploaded anything yet).
    -- This excludes transplant-only and NULL-kidney-type-only patients.
    AND (
        EXISTS (
            SELECT 1 FROM pathology pa
            WHERE pa.patient_id = p.id
              AND pa.kidney_type = 'NATIVE'
        )
        OR NOT EXISTS (
            SELECT 1 FROM pathology pa
            WHERE pa.patient_id = p.id
        )
    )

    -- MISSING: no native pathology report uploaded yet
    AND NOT EXISTS (
        SELECT 1
        FROM pathology pa_native
        WHERE pa_native.patient_id = p.id
          AND pa_native.kidney_type = 'NATIVE'
    )
)
SELECT
    patient_id,
    diagnosed_date,
    recruited_date,
    date_of_birth,
    age,
    hospital_name,
    hospital_code
FROM hospital_ranked
WHERE rn = 1
ORDER BY recruited_date DESC, patient_id;
"""


SQL_BIOPSY_TOTAL_ELIGIBLE = """
SELECT COUNT(DISTINCT pd.patient_id) AS total_eligible
FROM patient_diagnoses pd
JOIN group_patients gp ON gp.patient_id = pd.patient_id
JOIN groups gr         ON gr.id = gp.group_id
WHERE pd.biopsy IS TRUE
  AND gr.type = 'HOSPITAL'
  AND pd.patient_id NOT IN (
      SELECT id FROM patients WHERE test = TRUE OR control = TRUE
  );
"""


#####################################################################################
# GENETICS PAGE QUERIES
#####################################################################################

SQL_GENETICS_MISSING = """
WITH hospital_ranked AS (
  SELECT
      pd.patient_id,
      pd.from_date::date                                              AS diagnosed_date,
      pd.created_date::date                                           AS recruited_date,
      pdemo.date_of_birth,
      EXTRACT(YEAR FROM AGE(CURRENT_DATE, pdemo.date_of_birth))::int  AS age,
      gr.name                                                         AS hospital_name,
      gr.code                                                         AS hospital_code,
      ROW_NUMBER() OVER (
        PARTITION BY pd.patient_id
        ORDER BY gp.from_date DESC NULLS LAST, pd.created_date DESC, gp.id ASC
      ) AS rn
  FROM patient_diagnoses pd
  JOIN patients p             ON p.id          = pd.patient_id
  JOIN patient_demographics pdemo ON pdemo.patient_id = pd.patient_id
  JOIN group_patients gp      ON gp.patient_id = pd.patient_id
  JOIN groups gr               ON gr.id         = gp.group_id
  WHERE pd.gene_test IS TRUE
    AND pd.patient_id NOT IN (
        SELECT id FROM patients WHERE test = TRUE OR control = TRUE
    )
    AND NOT EXISTS (
        SELECT 1 FROM genetics ga WHERE ga.patient_id = p.id
    )
    AND gr.type = 'HOSPITAL'
)
SELECT
    patient_id,
    diagnosed_date,
    recruited_date,
    date_of_birth,
    age,
    hospital_name,
    hospital_code
FROM hospital_ranked
WHERE rn = 1
ORDER BY recruited_date DESC, patient_id;
"""


SQL_GENETICS_TOTAL_ELIGIBLE = """
SELECT COUNT(DISTINCT pd.patient_id) AS total_eligible
FROM patient_diagnoses pd
JOIN patients p        ON p.id          = pd.patient_id
JOIN group_patients gp ON gp.patient_id = pd.patient_id
JOIN groups gr          ON gr.id         = gp.group_id
WHERE pd.gene_test IS TRUE
  AND gr.type = 'HOSPITAL'
  AND pd.patient_id NOT IN (
      SELECT id FROM patients WHERE test = TRUE OR control = TRUE
  );
"""


#####################################################################################
# DIAGNOSES PAGE QUERIES
#####################################################################################

SQL_DIAGNOSES_MISSING = """
WITH missing_diagnoses AS (
    SELECT
        p.id AS patient_id,
        pdemo.date_of_birth,
        EXTRACT(YEAR FROM AGE(CURRENT_DATE, pdemo.date_of_birth))::int AS age,
        pdemo.created_date
    FROM patients p
    JOIN patient_demographics pdemo
        ON pdemo.patient_id = p.id
    WHERE NOT EXISTS (
        SELECT 1
        FROM patient_diagnoses pd
        WHERE pd.patient_id = p.id
    )
    AND NOT (p.test IS TRUE OR p.control IS TRUE)
    AND pdemo.source_type = 'RADAR'
),

latest_hospital AS (
    SELECT
        gp.patient_id,
        gr.name AS hospital_name,
        gr.code AS hospital_code,
        ROW_NUMBER() OVER (
            PARTITION BY gp.patient_id
            ORDER BY gp.from_date DESC NULLS LAST, gp.id DESC
        ) AS rn
    FROM group_patients gp
    JOIN groups gr
        ON gr.id = gp.group_id
    WHERE gr.type = 'HOSPITAL'
),

cohort_group AS (
    SELECT
        gp.patient_id,
        gr.name AS cohort_group,
        ROW_NUMBER() OVER (
            PARTITION BY gp.patient_id
            ORDER BY gp.from_date DESC NULLS LAST, gp.id DESC
        ) AS rn
    FROM group_patients gp
    JOIN groups gr
        ON gr.id = gp.group_id
    WHERE gr.type = 'COHORT'
)

SELECT DISTINCT
    md.patient_id,
    md.age,
    lh.hospital_name,
    lh.hospital_code,
    cg.cohort_group,
    md.created_date::date AS recruited_date
FROM missing_diagnoses md
LEFT JOIN latest_hospital lh
    ON lh.patient_id = md.patient_id
   AND lh.rn = 1
LEFT JOIN cohort_group cg
    ON cg.patient_id = md.patient_id
   AND cg.rn = 1
ORDER BY md.patient_id;
"""


SQL_DIAGNOSES_TOTAL_ELIGIBLE = """
SELECT COUNT(DISTINCT p.id) AS total_eligible
FROM patients p
JOIN patient_demographics pdemo
    ON pdemo.patient_id = p.id
WHERE pdemo.source_type = 'RADAR'
  AND NOT (p.test IS TRUE OR p.control IS TRUE);
"""


#####################################################################################
# ADULT DATA QUALITY QUERY
#####################################################################################

# Adults = age >= 18, hospital-linked, excluding the 13 BAPN paediatric sites.
# eGFR comes from data linkage (observation_id = 47), not Schwartz-computed.
SQL_ADULT_ALL_VALUES = f"""
WITH adult_patients AS (
    SELECT DISTINCT ON (gp.patient_id)
        gp.patient_id,
        g.name AS hospital_name
    FROM group_patients gp
    JOIN groups g
        ON g.id = gp.group_id
    JOIN patient_demographics pd
        ON pd.patient_id = gp.patient_id
       AND pd.source_type = 'RADAR'
    WHERE g.type = 'HOSPITAL'
      AND g.id NOT IN {_EXCLUDED_COHORT_IDS}
      AND pd.date_of_birth IS NOT NULL
      AND DATE_PART('year', AGE(pd.date_of_birth))::int >= 18
    ORDER BY gp.patient_id, gp.from_date DESC NULLS LAST
),
safe_results AS (
    SELECT
        r.patient_id,
        r.observation_id,
        r.date,
        CASE
            WHEN r.value ~ '^-?[0-9]+\\.?[0-9]*$'
            THEN r.value::numeric
        END AS num_value
    FROM results r
    JOIN adult_patients ap ON ap.patient_id = r.patient_id
    WHERE r.observation_id IN (47, 46, 45, 1, 2, 25, 24, 21, 23, 42, 43, 44, 73, 26, 75, 65, 56, 74, 27, 62)
      AND r.date IS NOT NULL
      AND r.date >= '1990-01-01'
)
SELECT
    ap.patient_id,
    ap.hospital_name,
    DATE_PART('year', sr.date)::int                                         AS obs_year,
    MAX(CASE WHEN sr.observation_id = 47 THEN sr.num_value END)             AS egfr,
    MAX(CASE WHEN sr.observation_id = 46 THEN sr.num_value END)             AS creatinine,
    MAX(CASE WHEN sr.observation_id = 45 THEN sr.num_value END)             AS urea,
    MAX(CASE WHEN sr.observation_id = 1  THEN sr.num_value END)             AS acr,
    MAX(CASE WHEN sr.observation_id = 2  THEN sr.num_value END)             AS pcr,
    MAX(CASE WHEN sr.observation_id = 25 THEN sr.num_value END)             AS systolic_bp,
    MAX(CASE WHEN sr.observation_id = 24 THEN sr.num_value END)             AS diastolic_bp,
    MAX(CASE WHEN sr.observation_id = 21 THEN sr.num_value END)             AS weight,
    MAX(CASE WHEN sr.observation_id = 23 THEN sr.num_value END)             AS bmi,
    MAX(CASE WHEN sr.observation_id = 42 THEN sr.num_value END)             AS sodium,
    MAX(CASE WHEN sr.observation_id = 43 THEN sr.num_value END)             AS potassium,
    MAX(CASE WHEN sr.observation_id = 44 THEN sr.num_value END)             AS bicarbonate,
    MAX(CASE WHEN sr.observation_id = 73 THEN sr.num_value END)             AS phosphate,
    MAX(CASE WHEN sr.observation_id = 26 THEN sr.num_value END)             AS calcium_adj,
    MAX(CASE WHEN sr.observation_id = 75 THEN sr.num_value END)             AS pth,
    MAX(CASE WHEN sr.observation_id = 65 THEN sr.num_value END)             AS haemoglobin,
    MAX(CASE WHEN sr.observation_id = 56 THEN sr.num_value END)             AS ferritin,
    MAX(CASE WHEN sr.observation_id = 74 THEN sr.num_value END)             AS vitamin_d,
    MAX(CASE WHEN sr.observation_id = 27 THEN sr.num_value END)             AS albumin,
    MAX(CASE WHEN sr.observation_id = 62 THEN sr.num_value END)             AS hba1c
FROM adult_patients ap
JOIN safe_results sr ON sr.patient_id = ap.patient_id
GROUP BY ap.patient_id, ap.hospital_name, DATE_PART('year', sr.date)
HAVING MAX(sr.num_value) IS NOT NULL
ORDER BY ap.patient_id, obs_year;
"""


SQL_ADULT_VALUES_BY_COHORT = """
WITH cohort_patients AS (
    SELECT DISTINCT gp.patient_id
    FROM group_patients gp
    JOIN patient_demographics pd
        ON pd.patient_id = gp.patient_id
       AND pd.source_type = 'RADAR'
       AND pd.date_of_birth IS NOT NULL
       AND DATE_PART('year', AGE(pd.date_of_birth))::int >= 18
    WHERE gp.group_id = %(cohort_id)s
),
patient_hospitals AS (
    SELECT DISTINCT ON (gp.patient_id)
        gp.patient_id,
        g.name AS hospital_name
    FROM group_patients gp
    JOIN groups g ON g.id = gp.group_id AND g.type = 'HOSPITAL'
    WHERE gp.patient_id IN (SELECT patient_id FROM cohort_patients)
    ORDER BY gp.patient_id, gp.from_date DESC NULLS LAST
),
safe_results AS (
    SELECT
        r.patient_id,
        r.observation_id,
        r.date,
        CASE
            WHEN r.value ~ '^-?[0-9]+\\.?[0-9]*$'
            THEN r.value::numeric
        END AS num_value
    FROM results r
    WHERE r.patient_id IN (SELECT patient_id FROM cohort_patients)
      AND r.observation_id IN (47,46,45,1,2,25,24,21,23,42,43,44,73,26,75,65,56,74,27,62)
      AND r.date IS NOT NULL
      AND r.date >= '1990-01-01'
)
SELECT
    ph.patient_id,
    ph.hospital_name,
    DATE_PART('year', sr.date)::int                                         AS obs_year,
    MAX(CASE WHEN sr.observation_id = 47 THEN sr.num_value END)             AS egfr,
    MAX(CASE WHEN sr.observation_id = 46 THEN sr.num_value END)             AS creatinine,
    MAX(CASE WHEN sr.observation_id = 45 THEN sr.num_value END)             AS urea,
    MAX(CASE WHEN sr.observation_id = 1  THEN sr.num_value END)             AS acr,
    MAX(CASE WHEN sr.observation_id = 2  THEN sr.num_value END)             AS pcr,
    MAX(CASE WHEN sr.observation_id = 25 THEN sr.num_value END)             AS systolic_bp,
    MAX(CASE WHEN sr.observation_id = 24 THEN sr.num_value END)             AS diastolic_bp,
    MAX(CASE WHEN sr.observation_id = 21 THEN sr.num_value END)             AS weight,
    MAX(CASE WHEN sr.observation_id = 23 THEN sr.num_value END)             AS bmi,
    MAX(CASE WHEN sr.observation_id = 42 THEN sr.num_value END)             AS sodium,
    MAX(CASE WHEN sr.observation_id = 43 THEN sr.num_value END)             AS potassium,
    MAX(CASE WHEN sr.observation_id = 44 THEN sr.num_value END)             AS bicarbonate,
    MAX(CASE WHEN sr.observation_id = 73 THEN sr.num_value END)             AS phosphate,
    MAX(CASE WHEN sr.observation_id = 26 THEN sr.num_value END)             AS calcium_adj,
    MAX(CASE WHEN sr.observation_id = 75 THEN sr.num_value END)             AS pth,
    MAX(CASE WHEN sr.observation_id = 65 THEN sr.num_value END)             AS haemoglobin,
    MAX(CASE WHEN sr.observation_id = 56 THEN sr.num_value END)             AS ferritin,
    MAX(CASE WHEN sr.observation_id = 74 THEN sr.num_value END)             AS vitamin_d,
    MAX(CASE WHEN sr.observation_id = 27 THEN sr.num_value END)             AS albumin,
    MAX(CASE WHEN sr.observation_id = 62 THEN sr.num_value END)             AS hba1c
FROM patient_hospitals ph
JOIN safe_results sr ON sr.patient_id = ph.patient_id
GROUP BY ph.patient_id, ph.hospital_name, DATE_PART('year', sr.date)
HAVING MAX(sr.num_value) IS NOT NULL
ORDER BY ph.patient_id, obs_year;
"""


#####################################################################################
# CHILDREN'S DASHBOARD QUERIES
#####################################################################################

SQL_CHILDREN_COMPLETENESS = f"""
WITH diagnoses AS (
    SELECT DISTINCT ON (pd_diag.patient_id)
        pd_diag.patient_id,
        pd_diag.from_date AS diagnoses_date
    FROM patient_diagnoses pd_diag
    JOIN patient_demographics pd
        ON pd.patient_id = pd_diag.patient_id
       AND pd.source_type = 'RADAR'
    WHERE pd_diag.from_date >= '2000-01-01'
      AND pd_diag.from_date >= pd.date_of_birth
    ORDER BY pd_diag.patient_id, pd_diag.from_date ASC
),

ages AS (
    SELECT DISTINCT ON (pd.patient_id)
        pd.patient_id,
        pd.date_of_birth,
        DATE_PART('year', AGE(pd.date_of_birth))::int                    AS current_age,
        DATE_PART('year', AGE(d.from_date, pd.date_of_birth))::int       AS age_at_diagnoses
    FROM patient_demographics pd
    JOIN (
        SELECT DISTINCT ON (patient_id)
            patient_id,
            from_date
        FROM patient_diagnoses
        ORDER BY patient_id, from_date ASC
    ) d ON d.patient_id = pd.patient_id
    WHERE pd.source_type = 'RADAR'
    ORDER BY pd.patient_id
),

hospitals AS (
    SELECT
        gp.patient_id,
        MAX(g.name) AS hospital_name
    FROM group_patients gp
    JOIN groups g ON g.id = gp.group_id
        AND g.code IN ('RBS25', 'RA723', 'RP4', '99RCSLB', 'RQ3', '11023',
                       'SGC02', 'RJ122', '99RHM01', '99RQR13', 'RTD01', 'RW3RM', 'RRBBV')
    GROUP BY gp.patient_id
),

cohorts AS (
    SELECT
        gp.patient_id,
        MAX(g.name) AS cohort_name
    FROM group_patients gp
    JOIN groups g ON g.id = gp.group_id AND g.type = 'COHORT'
    WHERE g.id NOT IN {_EXCLUDED_COHORT_IDS}
    GROUP BY gp.patient_id
),

year_spine AS (
    SELECT
        a.patient_id,
        generate_series(
            DATE_PART('year', CURRENT_DATE)::int - 18,
            DATE_PART('year', CURRENT_DATE)::int
        ) AS obs_year
    FROM ages a
    WHERE a.current_age < 18
),

obs_values AS (
    SELECT
        patient_id,
        DATE_PART('year', date)::int                                      AS obs_year,
        MAX(CASE WHEN observation_id = 22 THEN value END)                 AS height_cm,
        MAX(CASE WHEN observation_id = 46 THEN value END)                 AS creatinine_val
    FROM results
    WHERE observation_id IN (22, 46)
    GROUP BY patient_id, DATE_PART('year', date)
),

egfr_calc AS (
    SELECT
        patient_id,
        obs_year,
        CASE
            WHEN height_cm IS NOT NULL
             AND creatinine_val IS NOT NULL
             AND creatinine_val::numeric > 0
            THEN ROUND((36.5 * (height_cm::numeric / creatinine_val::numeric))::numeric, 2)
            ELSE NULL
        END AS egfr_value
    FROM obs_values
),

obs_presence AS (
    SELECT
        r.patient_id,
        DATE_PART('year', r.date)::int                                     AS obs_year,
        MAX(CASE WHEN r.observation_id = 22 THEN 1 ELSE 0 END)            AS has_height,
        MAX(CASE WHEN r.observation_id = 21 THEN 1 ELSE 0 END)            AS has_weight,
        MAX(CASE WHEN r.observation_id = 1  THEN 1 ELSE 0 END)            AS has_acr,
        MAX(CASE WHEN r.observation_id = 2  THEN 1 ELSE 0 END)            AS has_pcr,
        MAX(CASE WHEN r.observation_id = 24 THEN 1 ELSE 0 END)            AS has_diastolic_bp,
        MAX(CASE WHEN r.observation_id = 25 THEN 1 ELSE 0 END)            AS has_systolic_bp,
        MAX(CASE WHEN r.observation_id = 46 THEN 1 ELSE 0 END)            AS has_creatinine
    FROM results r
    WHERE r.observation_id IN (1, 2, 21, 22, 24, 25, 46)
    GROUP BY r.patient_id, DATE_PART('year', r.date)
)

SELECT
    ys.patient_id,
    h.hospital_name,
    c.cohort_name,
    TO_CHAR(d.diagnoses_date, 'DD/MM/YYYY')                              AS diagnoses_date,
    a.age_at_diagnoses,
    a.current_age,
    ys.obs_year,

    CASE WHEN ys.obs_year < DATE_PART('year', d.diagnoses_date)::int
         THEN NULL ELSE COALESCE(op.has_height, 0) END                   AS height,

    CASE WHEN ys.obs_year < DATE_PART('year', d.diagnoses_date)::int
         THEN NULL ELSE COALESCE(op.has_weight, 0) END                   AS weight,

    CASE WHEN ys.obs_year < DATE_PART('year', d.diagnoses_date)::int
         THEN NULL ELSE COALESCE(op.has_acr, 0) END                      AS acr,

    CASE WHEN ys.obs_year < DATE_PART('year', d.diagnoses_date)::int
         THEN NULL ELSE COALESCE(op.has_pcr, 0) END                      AS pcr,

    CASE WHEN ys.obs_year < DATE_PART('year', d.diagnoses_date)::int
         THEN NULL ELSE COALESCE(op.has_diastolic_bp, 0) END             AS diastolic_bp,

    CASE WHEN ys.obs_year < DATE_PART('year', d.diagnoses_date)::int
         THEN NULL ELSE COALESCE(op.has_systolic_bp, 0) END              AS systolic_bp,

    CASE WHEN ys.obs_year < DATE_PART('year', d.diagnoses_date)::int
         THEN NULL ELSE COALESCE(op.has_creatinine, 0) END               AS creatinine,

    CASE WHEN ys.obs_year < DATE_PART('year', d.diagnoses_date)::int
         THEN NULL
         ELSE CASE WHEN ec.egfr_value IS NOT NULL THEN 1 ELSE 0 END
    END                                                                   AS egfr

FROM year_spine ys
JOIN hospitals     h  ON h.patient_id = ys.patient_id
JOIN cohorts       c  ON c.patient_id = ys.patient_id
JOIN diagnoses     d  ON d.patient_id = ys.patient_id
JOIN ages          a  ON a.patient_id = ys.patient_id
LEFT JOIN obs_presence op
       ON op.patient_id = ys.patient_id
      AND op.obs_year   = ys.obs_year
LEFT JOIN egfr_calc ec
       ON ec.patient_id = ys.patient_id
      AND ec.obs_year   = ys.obs_year
ORDER BY ys.patient_id, ys.obs_year;
"""


SQL_CHILDREN_ALL_VALUES = """
WITH paediatric_patients AS (
    SELECT DISTINCT ON (gp.patient_id)
        gp.patient_id,
        g.name AS hospital_name
    FROM group_patients gp
    JOIN groups g
        ON g.id = gp.group_id
       AND g.code IN ('RBS25','RA723','RP4','99RCSLB','RQ3','11023',
                      'SGC02','RJ122','99RHM01','99RQR13','RTD01','RW3RM','RRBBV')
    JOIN patient_demographics pd
        ON pd.patient_id = gp.patient_id
       AND pd.source_type = 'RADAR'
    WHERE DATE_PART('year', AGE(pd.date_of_birth))::int < 18
    ORDER BY gp.patient_id, gp.from_date DESC NULLS LAST
),
safe_results AS (
    SELECT
        r.patient_id,
        r.observation_id,
        r.date,
        CASE
            WHEN r.value ~ '^-?[0-9]+\\.?[0-9]*$'
            THEN r.value::numeric
        END AS num_value
    FROM results r
    JOIN paediatric_patients pp ON pp.patient_id = r.patient_id
    WHERE r.observation_id IN (1, 2, 21, 22, 24, 25, 46)
      AND r.date IS NOT NULL
      AND r.date >= '1990-01-01'
)
SELECT
    pp.patient_id,
    pp.hospital_name,
    DATE_PART('year', sr.date)::int                                        AS obs_year,
    MAX(CASE WHEN sr.observation_id = 22 THEN sr.num_value END)            AS height,
    MAX(CASE WHEN sr.observation_id = 21 THEN sr.num_value END)            AS weight,
    MAX(CASE WHEN sr.observation_id = 1  THEN sr.num_value END)            AS acr,
    MAX(CASE WHEN sr.observation_id = 2  THEN sr.num_value END)            AS pcr,
    MAX(CASE WHEN sr.observation_id = 24 THEN sr.num_value END)            AS diastolic_bp,
    MAX(CASE WHEN sr.observation_id = 25 THEN sr.num_value END)            AS systolic_bp,
    MAX(CASE WHEN sr.observation_id = 46 THEN sr.num_value END)            AS creatinine
FROM paediatric_patients pp
JOIN safe_results sr ON sr.patient_id = pp.patient_id
GROUP BY pp.patient_id, pp.hospital_name, DATE_PART('year', sr.date)
HAVING MAX(sr.num_value) IS NOT NULL
ORDER BY pp.patient_id, obs_year;
"""


SQL_PATIENT_VALUES = """
SELECT
    DATE_PART('year', r.date)::int                                      AS obs_year,
    MAX(CASE WHEN r.observation_id = 22
             AND r.value ~ '^-?[0-9]+\\.?[0-9]*$'
             THEN r.value::numeric END)                                 AS height,
    MAX(CASE WHEN r.observation_id = 21
             AND r.value ~ '^-?[0-9]+\\.?[0-9]*$'
             THEN r.value::numeric END)                                 AS weight,
    MAX(CASE WHEN r.observation_id = 1
             AND r.value ~ '^-?[0-9]+\\.?[0-9]*$'
             THEN r.value::numeric END)                                 AS acr,
    MAX(CASE WHEN r.observation_id = 2
             AND r.value ~ '^-?[0-9]+\\.?[0-9]*$'
             THEN r.value::numeric END)                                 AS pcr,
    MAX(CASE WHEN r.observation_id = 24
             AND r.value ~ '^-?[0-9]+\\.?[0-9]*$'
             THEN r.value::numeric END)                                 AS diastolic_bp,
    MAX(CASE WHEN r.observation_id = 25
             AND r.value ~ '^-?[0-9]+\\.?[0-9]*$'
             THEN r.value::numeric END)                                 AS systolic_bp,
    MAX(CASE WHEN r.observation_id = 46
             AND r.value ~ '^-?[0-9]+\\.?[0-9]*$'
             THEN r.value::numeric END)                                 AS creatinine
FROM results r
WHERE r.patient_id = %(patient_id)s
  AND r.observation_id IN (1, 2, 21, 22, 24, 25, 46)
  AND r.date IS NOT NULL
GROUP BY DATE_PART('year', r.date)
ORDER BY obs_year;
"""



















