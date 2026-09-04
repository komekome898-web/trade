Source: Kenneth R. French Data Library (Tuck School of Business, Dartmouth)
  https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
  https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Japan_3_Factors_CSV.zip
  https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Japan_Mom_Factor_CSV.zip
Fetched: 2026-09-04 (audit AM / claim JPL3). File header states "created using the
202607 Bloomberg database" -- monthly coverage 1990-07..2026-07 (3 factors) and
1990-11..2026-07 (momentum). Values are monthly percent returns; -99.99 = missing.
Annual-average rows at the end of each CSV were not used (monthly rows only).
No SMB/HML/Mkt-RF/WML values were altered; only the monthly block was parsed
(see /tmp .../scratchpad/audit_AM.py, not included in this snapshot).
