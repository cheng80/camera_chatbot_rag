# Documentation Index

이 문서는 프로젝트 문서의 위치와 읽는 순서를 정리한다.

새 세션에서는 먼저 [NEXT_SESSION.md](../NEXT_SESSION.md)를 읽고 현재 진행 상황과
다음 작업을 확인한다.

## Core

- [초기 설계 문서](Panasonic_LUMIX_Manual_Assistant_GCSE_Initial_Design.md): 프로젝트 원본 설계와 장기 방향

## Architecture

- [아키텍처 개요](architecture/overview.md): 시스템 구성과 주요 컴포넌트
- [RAG 파이프라인](architecture/rag_pipeline.md): 검색 증강 생성(RAG) 처리 흐름
- [Graph-lite ERD](architecture/graph_lite_erd.md): 기능/모델/문서 관계 구조

## API

- [API 명세](api/api_spec.md): FastAPI 엔드포인트와 응답 구조

## Data

- [데이터 인벤토리](data/data_inventory.md): 원본 PDF와 처리 산출물 목록
- [PDF 로더 후보 검토](data/pdf_loader_options.md): OpenDataLoader PDF primary와 pypdf fallback 정책

## Evaluation

- [평가 리포트](evaluation/evaluation_report.md): 로더/검색 품질 평가 결과

## Reference

- [용어 사전](reference/glossary.md): RAG 초급자를 위한 한글/영문 용어와 기능 설명
