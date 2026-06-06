# Data Inventory

원본 PDF 문서 등록과 추출 결과를 추적합니다.

## Summary

| 항목 | 값 |
|---|---:|
| 등록 문서 | 29 |
| 등록 모델 | 30 |
| 추출 완료 문서 | 29 |
| 전체 페이지(Page) | 16,532 |
| 전체 청크(Chunk) | 302,304 |
| FTS5 색인(Index) | 생성 완료 |
| 한국어 보조 색인 | trigram |
| pypdf fallback | 0 |

산출물:

```text
data/processed/pages/{document_id}.jsonl
data/processed/chunks/{document_id}.jsonl
data/processed/reports/extraction_report.json
data/indexes/fts/lumix_manuals.sqlite3
```

`data/processed/*`와 `data/indexes/*` 산출물은 로컬 생성 파일이며 Git에 올리지
않습니다.

## Documents

| document_id | 파일명 | 모델 | 로더 | 페이지 | 청크 | 상태 |
|---|---|---|---|---:|---:|---|
| dc_g100d_full_kor | DC-G100D_DVQP3105_full_kor.pdf | DC-G100D | opendataloader | 503 | 7,255 | extracted |
| dc_g100_kor | DC-G100_DVQP2194ZC_kor.pdf | DC-G100 | opendataloader | 513 | 7,487 | extracted |
| dc_g95_kor | DC-G95_DVQP1916ZA_kor.pdf | DC-G95 | opendataloader | 345 | 7,706 | extracted |
| dc_g9m2_full_kor | DC-G9M2_DVQP3025_full_kor.pdf | DC-G9M2 | opendataloader | 929 | 14,778 | extracted |
| dc_g9_full_kor | DC-G9_DVQP1424ZE_full_kor.pdf | DC-G9 | opendataloader | 377 | 8,569 | extracted |
| dc_gf10_kor | DC-GF10_DVQP1677ZA_kor.pdf | DC-GF10 | opendataloader | 330 | 6,881 | extracted |
| dc_gf9_kor | DC-GF9_DVQP1212ZA_kor.pdf | DC-GF9 | opendataloader | 323 | 6,795 | extracted |
| dc_gh5s_full_kor | DC-GH5S_DVQP1460ZE_full_kor.pdf | DC-GH5S | opendataloader | 398 | 9,420 | extracted |
| dc_gh5_full_kor | DC-GH5_DVQP1138ZD_full_kor.pdf | DC-GH5 | opendataloader | 380 | 9,457 | extracted |
| dc_gh6_full_kor | DC-GH6_DVQP2458_full_kor.pdf | DC-GH6 | opendataloader | 908 | 12,910 | extracted |
| dc_gh7_full_kor | DC-GH7_DVQP3124_full_kor.pdf | DC-GH7 | opendataloader | 1,034 | 17,258 | extracted |
| dc_gx9_kor | DC-GX9_DVQP1483ZA_kor.pdf | DC-GX9 | opendataloader | 342 | 6,964 | extracted |
| dc_lx100m2_kor | DC-LX100M2_DVQP1791ZA_kor.pdf | DC-LX100M2 | opendataloader | 308 | 6,718 | extracted |
| dc_s1h_full_kor | DC-S1H_DVQP2041ZE_full_kor.pdf | DC-S1H | opendataloader | 658 | 12,360 | extracted |
| dc_s1m2_full_kor | DC-S1M2_DVQP3242_full_kor.pdf | DC-S1M2 | opendataloader | 1,079 | 19,279 | extracted |
| dc_s1m2es_full_kor | DC-S1M2ES_DVQP3370_full_kor.pdf | DC-S1M2ES | opendataloader | 1,047 | 17,531 | extracted |
| dc_s1rm2_full_kor | DC-S1RM2_DVQP3260_full_kor.pdf | DC-S1RM2 | opendataloader | 1,086 | 18,471 | extracted |
| dc_s1r_full_kor | DC-S1R_DVQP1866ZG_full_kor.pdf | DC-S1R | opendataloader | 569 | 10,302 | extracted |
| dc_s1_full_kor | DC-S1_DVQP1890ZG_full_kor.pdf | DC-S1 | opendataloader | 605 | 11,310 | extracted |
| dc_s5m2x_full_kor | DC-S5M2X_DVQP3007_full_kor.pdf | DC-S5M2X | opendataloader | 1,038 | 17,837 | extracted |
| dc_s5m2_full_kor | DC-S5M2_DVQP2855_full_kor.pdf | DC-S5M2 | opendataloader | 981 | 14,743 | extracted |
| dc_s5_full_kor | DC-S5_DVQP2218ZD_full_kor.pdf | DC-S5 | opendataloader | 598 | 10,607 | extracted |
| dc_tz99_zs99_full_kor | DC-TZ99_ZS99_DVQP3300_full_kor.pdf | DC-TZ99 / DC-ZS99 | opendataloader | 285 | 5,712 | extracted |
| dmc_g85_full_kor | DMC-G85_DVQP1024ZA_kor.pdf | DMC-G85 | opendataloader | 338 | 7,592 | extracted |
| dmc_gf1_kor | DMC-GF1-KOR.pdf | DMC-GF1 | opendataloader | 196 | 5,803 | extracted |
| dmc_gm1_kor | DMC-GM1-KOR.pdf | DMC-GM1 | opendataloader | 350 | 6,870 | extracted |
| dmc_gm5_kor | DMC-GM5-KOR.pdf | DMC-GM5 | opendataloader | 367 | 7,961 | extracted |
| dmc_gx85_kor | DMC-GX85-KOR.pdf | DMC-GX85 | opendataloader | 337 | 7,607 | extracted |
| dmc_lx10_kor | DMC-LX10_SQW0745_kor.pdf | DMC-LX10 | opendataloader | 308 | 6,121 | extracted |
