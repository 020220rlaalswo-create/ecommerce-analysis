# Olist 이커머스 데이터 분석 포트폴리오

**SQL + Python / Pandas + Matplotlib | 데이터 정제 → 핵심 성과 지표 → 시각화 → 비즈니스 해석**

브라질 Olist 익명화 주문 데이터를 사용해 **매출, 주문, 배송 품질, 만족도 및 재구매**를 분석하는 재현 가능한 개인 프로젝트입니다.

## 실제 데이터 분석 결과

Olist 원본 CSV를 사용하여 GitHub Actions에서 분석을 실행했고, 주문 단위 중복 검증·매출 대조·지표 범위 검증을 통과했습니다.

| 핵심 지표 | 실제 분석값 |
|---|---:|
| 전체 주문 | **99,441건** |
| 배송 완료 주문 | **96,478건** |
| 배송 완료 주문의 고유 고객 | **93,358명** |
| 배송 완료 상품 매출 (배송비 제외) | **13,221,498.11 BRL** |
| 평균 배송 소요일 | **12.56일** |
| 배송 지연율 | **8.11%** (96,470건 기준) |
| 관측 기간 재구매 고객 비율 | **3.00%** (93,358명 기준) |

> 상품 매출은 배송 완료 주문의 상품 가격 합계로, 회계상 확정 순매출이나 이익과 다릅니다. 재구매율은 관측 기간 내 비율입니다.

### 1. 월별 상품 매출

![월별 상품 매출](reports/01_monthly_revenue.png)

### 2. 매출 상위 상품 카테고리

![매출 상위 상품 카테고리](reports/02_category_revenue.png)

### 3. 전체 주문 처리 상태

![전체 주문 처리 상태](reports/03_order_status.png)

### 4. 배송 소요일 분포

![배송 소요일 분포](reports/04_delivery_days.png)

### 5. 지역별 배송 지연율

![지역별 배송 지연율](reports/05_late_delivery_states.png)

### 6. 관측 기간 고객 재구매 분포

![고객 재구매 분포](reports/06_repeat_customers.png)

### 7. 배송 지연 여부에 따른 평균 리뷰 점수

![배송 지연과 리뷰 점수](reports/07_review_vs_lateness.png)

**[전체 분석 결과 보고서 보기](reports/README.md)** · **[Python 분석 코드 보기](src/analyze.py)** · **[SQL 분석 코드 보기](sql/analysis.sql)**

## 문제 정의
- 어떤 카테고리와 시기에 판매가 집중되는가?
- 예상 배송일을 넘기는 주문은 어디에 집중되는가?
- 지연 배송과 낮은 고객 평가는 연관되는가?
- 관측된 기간 내 고유 고객의 재구매 패턴은 어떤가?

## 데이터
공식 출처: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (2016~2018년 익명화 데이터, **CC BY-NC-SA 4.0**).

원본 CSV는 리포지토리에 포함하지 않으며 `data/README.md`에 9개 파일 다운로드 및 라이선스를 안내합니다. 기본 분석에 필요한 것은 8개 CSV로, 지리좌표 파일은 선택 사항입니다.

## 실행
```bash
git clone https://github.com/020220rlaalswo-create/ecommerce-analysis.git
cd ecommerce-analysis
python -m pip install -r requirements.txt
# Kaggle에서 내려받은 CSV 8개를 data/raw/ 아래에 배치
python src/analyze.py --data-dir data/raw --out-dir outputs
```

실행하면 `outputs/`에 **주문 단위 데이터, 고객 요약, 월별/카테고리 집계, KPI JSON, 시각화 7장**이 생성됩니다. CSV 없이 실행하면 누락 파일을 명확히 알려줍니다.

## 결과물
| 위치 | 역할 |
|---|---|
| `src/analyze.py` | 다중 테이블 조인/정합성 검증/집계 및 차트 |
| `sql/analysis.sql` | MySQL 8.0 주문 단위/매출/재구매/리뷰 질의 |
| `docs/INSIGHTS.md` | KPI 정의, 해석 가이드, 비즈니스 제안과 한계 |
| `data/README.md` | 데이터 출처, 재현 방법, 라이선스 |
| `outputs/` | 로컬 실행으로 생성되는 차트와 요약 (Git 추적 제외) |

## 분석 설계상 핵심 사항
1. `order_items`, `order_payments`, `order_reviews`를 먼저 주문 단위로 집계하여 **1:N×1:N 조인으로 매출이 중복되는 문제 방지**.
2. `customer_id` 대신 `customer_unique_id`로 고유 고객 및 재구매를 계산.
3. 상품 가격 기준 거래규모, 결제금액, 운임을 **서로 다른 지표**로 분리.
4. 지연율은 **예상일과 실제 배송일이 모두 기록된 배송 완료 주문**만 분모로 계산.
5. 실제 클릭·방문·장바구니 로그가 없어 **방문→구매 퍼널 분석은 불가능**하다는 한계 명시.
6. 2018년 이후 관측 부재와 관측 길이의 차이 때문에 재구매율을 장기 고객 유지율로 해석하지 않음.

## 그래프 및 재현 방법
위의 7개 그래프는 [reports/](reports/)에 저장된 실제 생성 이미지입니다. 분석을 재실행하려면 원본 Olist CSV를 `data/raw/`에 배치하고 `python src/analyze.py`를 실행하세요.


## 사용 기술
MySQL 8.0, Python 3.10+, pandas, NumPy, Matplotlib, Seaborn

---
데이터 제공: Olist / Kaggle. 비상업적 교육용 분석이며 원본 데이터 라이선스는 CC BY-NC-SA 4.0입니다.
