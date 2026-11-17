# Baseline summary

## Network-wide

| metric                        |   value |
|:------------------------------|--------:|
| Students                      |  500    |
| Course records (interactions) | 2044    |
| Average quiz score (%)        |   62.9  |
| Course completion rate (%)    |   57.4  |
| Interactions per student      |    4.09 |
| Average hours per student     |   83.6  |
| Students flagged at risk (%)  |   22    |

## By city (temporary stand-in for school)

| city      |   students |   avg_quiz_score |   completion_rate_pct |   interactions_per_student |   at_risk_pct |
|:----------|-----------:|-----------------:|----------------------:|---------------------------:|--------------:|
| Ahmedabad |         42 |             66.7 |                  63.3 |                        4   |          14.3 |
| Hyderabad |         46 |             64.8 |                  57.8 |                        3.8 |          19.6 |
| Kolkata   |         66 |             64.5 |                  59.4 |                        4   |          21.2 |
| Jaipur    |         39 |             63.9 |                  59.1 |                        4.2 |          15.4 |
| Chennai   |         62 |             63.3 |                  58.4 |                        4.4 |          19.4 |
| Mumbai    |         59 |             63.2 |                  58.6 |                        4.3 |          22   |
| Pune      |         45 |             62.1 |                  63.3 |                        4   |          17.8 |
| Kochi     |         49 |             60.4 |                  54.7 |                        3.8 |          28.6 |
| Bengaluru |         41 |             59.8 |                  53.9 |                        4.1 |          29.3 |
| Delhi     |         51 |             59.4 |                  50.2 |                        4.3 |          31.4 |

## By course_id (stand-in for subject), sorted by completion rate

| course_id   |   records |   avg_quiz_score |   completion_rate_pct |   avg_hours |
|:------------|----------:|-----------------:|----------------------:|------------:|
| CRS-003     |       154 |             66.6 |                  78.6 |        20.1 |
| CRS-010     |       136 |             65.5 |                  74.3 |        21.6 |
| CRS-014     |       133 |             65.8 |                  72.9 |         9.4 |
| CRS-001     |       132 |             67.8 |                  72   |        22.4 |
| CRS-005     |       151 |             64.6 |                  70.2 |        14.7 |
| CRS-006     |       131 |             65.2 |                  68.7 |        12.7 |
| CRS-013     |       131 |             63.3 |                  55   |        19.3 |
| CRS-002     |       133 |             62.1 |                  54.1 |        29.2 |
| CRS-011     |       154 |             63.9 |                  53.9 |        16.9 |
| CRS-007     |       132 |             61.4 |                  53   |        27.2 |
| CRS-008     |       131 |             61.2 |                  50.4 |        14.1 |
| CRS-015     |       143 |             61.1 |                  42   |        22.2 |
| CRS-009     |       130 |             58.6 |                  37.7 |        20.1 |
| CRS-004     |       117 |             58.4 |                  37.6 |        28.4 |
| CRS-012     |       136 |             54.6 |                  34.6 |        29.9 |

## By student profile

| profile            |   students |   avg_quiz_score |   completion_rate_pct |   interactions_per_student |   at_risk_pct |
|:-------------------|-----------:|-----------------:|----------------------:|---------------------------:|--------------:|
| Analytics Track    |         84 |             64.2 |                  62.2 |                        4.4 |          20.2 |
| Career Switcher    |         99 |             63.7 |                  57.3 |                        4.1 |          19.2 |
| AI/ML Enthusiast   |         96 |             63.3 |                  53.4 |                        4.1 |          27.1 |
| Data Analyst Track |        123 |             61.8 |                  56.9 |                        3.9 |          22.8 |
| Full Stack + ML    |         98 |             61.6 |                  60.2 |                        4   |          20.4 |

## Enrollments file by course (not joinable to students)

| course               |   enrollments |   completion_rate_pct |   avg_score_pct |
|:---------------------|--------------:|----------------------:|----------------:|
| Machine Learning     |            54 |                  77.8 |            65.8 |
| Finance Fundamentals |            37 |                  70.3 |            66.3 |
| Data Science         |            47 |                  70.2 |            67.5 |
| Python Basics        |            48 |                  68.8 |            70.8 |
| UI Design            |            50 |                  68   |            69.3 |
| Cybersecurity        |            56 |                  67.9 |            71.5 |
| Web Dev              |            52 |                  65.4 |            68.9 |
| Cloud Computing      |            64 |                  62.5 |            67.9 |
| Digital Marketing    |            45 |                  62.2 |            67.4 |
| Business Analytics   |            44 |                  47.7 |            67.2 |

## Highlights

- Highest average quiz score by city: Ahmedabad (66.7); lowest: Delhi (59.4).
- Highest completion rate by course: CRS-003 (78.6%); lowest: CRS-012 (34.6%).
- Grade breakdown is not available: there is no grade column in any file.
