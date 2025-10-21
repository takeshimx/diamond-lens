# Statistical Analysis Methods

## Overview

This document describes the statistical analysis methods implemented in the Diamond Lens project for predictive modeling and hypothesis testing.

---

## 1. Hypothesis Testing

### Purpose
Analyze whether there is a statistically significant difference in batting performance between different conditions (e.g., left-handed vs. right-handed pitchers).

### Method: Independent Samples T-Test

**Implementation**: `analysis/hypothesis_testing.ipynb`

**Example Analysis**: "Do batters perform differently against left-handed vs. right-handed pitchers?"

**Steps**:
1. Data extraction from BigQuery
2. T-test execution using `scipy.stats.ttest_ind`
3. Effect size calculation (Cohen's d)
4. 95% confidence interval computation
5. Visualization (box plots, violin plots)

**Results**:
- **p-value**: Statistical significance indicator (p < 0.05 indicates significant difference)
- **Cohen's d**: Effect size magnitude
  - 0.2: Small effect
  - 0.5: Medium effect
  - 0.8: Large effect
- **95% CI**: Confidence interval of the difference

**Business Interpretation**:
- Identifies player strengths and weaknesses in specific matchups
- Informs lineup construction and player utilization strategies

---

## 2. Multivariate Regression Analysis

### Purpose
Predict team win rates based on offensive (OPS) and pitching (ERA, HRs allowed) metrics.

### Method: Multiple Linear Regression

**Implementation**:
- Notebook: `analysis/regression_analysis.ipynb`
- Production API: BigQuery ML model + FastAPI endpoints

### Model Development Process

#### Phase 1: Simple Linear Regression (Baseline)
**Features**: OPS only

**Results**:
- R² = 0.47
- RMSE = 0.040
- **Conclusion**: OPS alone explains only 47% of win rate variance

#### Phase 2: Multivariate Regression (Improved)
**Features**: OPS, ERA, Home Runs Allowed

**Variable Selection Process**:
1. **Candidate Variables**: OPS, AVG, ERA, WHIP, HRs Allowed, Stolen Bases, Strikeouts
2. **Multicollinearity Check**: VIF (Variance Inflation Factor) analysis
   - Removed AVG (VIF = 5.23, correlation with OPS)
   - Removed SB, SO (coefficients ≈ 0, minimal impact)
3. **Final Variables**: OPS, ERA, HRs Allowed

**Results**:
- **R² = 0.942** (94.2% of variance explained)
- **RMSE = 0.0253** (±4 wins per season prediction error)
- **MAE = 0.0157**

**Regression Equation**:
```
win_rate = 1.179 * OPS - 0.093 * ERA - 0.0002 * hrs_allowed + intercept
```

**Interpretation**:
- OPS increase by 0.01 → win rate +0.0118 (≈2 more wins/season)
- ERA increase by 1.00 → win rate -0.093 (≈15 fewer wins/season)
- HRs allowed have minimal direct impact (captured in ERA)

---

## 3. Multicollinearity Analysis

### Purpose
Identify and remove correlated predictor variables to improve model stability and interpretability.

### Method: Variance Inflation Factor (VIF)

**Implementation**: `analysis/regression_analysis.ipynb`

**VIF Interpretation**:
- VIF < 5: No multicollinearity
- VIF 5-10: Moderate multicollinearity (caution)
- VIF > 10: High multicollinearity (remove variable)

**Analysis Results**:

| Variable | VIF | Decision |
|----------|-----|----------|
| OPS | 4.58 | ✅ Keep |
| AVG | 5.23 | ⚠️ Remove (correlated with OPS) |
| ERA | 2.55 | ✅ Keep |
| HRs Allowed | 2.15 | ✅ Keep |
| SO | 1.73 | ✅ Keep (but coefficient ≈ 0) |
| SB | 1.01 | ✅ Keep (but coefficient ≈ 0) |

**Standardized Coefficients** (for importance ranking):

| Variable | Standardized Coefficient | Importance |
|----------|-------------------------|------------|
| ERA | -0.0514 | ★★★ Most important |
| OPS | 0.0434 | ★★★ Most important |
| HRs Allowed | -0.0030 | ★ Minor |
| SB | 0.0009 | ☆ Negligible |
| SO | -0.0008 | ☆ Negligible |

**Key Insight**:
Standardized coefficients revealed that despite large raw coefficients for SB and SO in BigQuery ML (7.89, -2.44), their actual impact is minimal when accounting for scale differences. This prevented overfitting and improved model interpretability.

---

## 4. Model Evaluation

### Metrics

**R² (Coefficient of Determination)**:
- Measures proportion of variance explained by the model
- Range: 0 to 1 (higher is better)
- Our model: 0.942 (excellent)

**RMSE (Root Mean Squared Error)**:
- Average prediction error in win rate units
- Our model: 0.0253 (±4 wins per 162-game season)

**MAE (Mean Absolute Error)**:
- Average absolute prediction error
- Our model: 0.0157 (±2.5 wins per season)

### Residual Analysis

**Implementation**: `analysis/regression_analysis.ipynb`

**Checks**:
1. **Residual plot**: Verify constant variance (homoscedasticity)
2. **Normality test**: Shapiro-Wilk test for residual normality
3. **Outlier detection**: Identify teams with unusual win rates

**Results**:
- Residuals show no systematic patterns
- Residuals approximately normally distributed
- No significant outliers detected

---

## 5. Production Deployment

### BigQuery ML Model

**Model**: `tksm-dash-test-25.mlb_analytics_dash_25.predict_winrate_from_ops_multivariate`

**Features**:
- Automated training on updated data
- Real-time prediction via SQL
- Version control via BigQuery ML

**Model Weights**:
```sql
SELECT processed_input, weight
FROM ML.WEIGHTS(MODEL `predict_winrate_from_ops_multivariate`);
```

### FastAPI Integration

**Endpoints**:
- `GET /api/v1/statistics/predict-winrate`: Real-time predictions
- `GET /api/v1/statistics/model-summary`: Model evaluation metrics
- `GET /api/v1/statistics/ops-sensitivity`: Sensitivity analysis

**Example Usage**:
```bash
curl "http://localhost:8000/api/v1/statistics/predict-winrate?team_ops=0.750&team_era=4.20&team_hrs_allowed=180"
```

**Response**:
```json
{
  "predicted_win_rate": 0.5328,
  "expected_wins_per_season": 86,
  "model_metrics": {
    "r2_score": 0.942,
    "mae": 0.0157
  }
}
```

---

## 6. Limitations and Future Work

### Current Limitations

1. **Scope**: Model predicts team-level win rates only (not individual player impact)
2. **Time Period**: Trained on 2021-2024 data (may not generalize to different eras)
3. **Missing Variables**:
   - Defense metrics (DRS, UZR)
   - Bullpen strength
   - Home/away splits
4. **Causality**: Model shows correlation, not causation

### Future Improvements

1. **Feature Engineering**:
   - Add defensive metrics
   - Include team chemistry proxies
   - Incorporate schedule strength

2. **Model Complexity**:
   - Experiment with non-linear models (Random Forest, XGBoost)
   - Time series forecasting for in-season predictions

3. **Validation**:
   - Cross-validation across multiple seasons
   - Out-of-sample testing on 2025 season

---

## 7. Key Learnings

### Why This Approach Works

**Multi-dimensional Evaluation**:
- OPS captures offensive production
- ERA captures pitching quality
- The combination explains 94% of win rate variance

**Statistical Rigor**:
- VIF analysis prevented multicollinearity issues
- Hypothesis testing validated assumptions
- Residual analysis confirmed model validity

### Business Value

**For Team Management**:
- Quantify impact of offensive vs. pitching improvements
- Prioritize resource allocation (hitting coach vs. pitching acquisitions)
- Set realistic win total expectations

**For Analytics Teams**:
- Demonstrates end-to-end ML workflow
- Shows importance of variable selection
- Highlights production deployment considerations

---

## References

### Statistical Methods
- T-test: Student's t-distribution for independent samples
- VIF: Variance Inflation Factor for multicollinearity detection
- Cohen's d: Standardized effect size measure

### Implementation Tools
- **Python**: scipy, scikit-learn, pandas, numpy
- **Visualization**: matplotlib, seaborn
- **Production**: BigQuery ML, FastAPI
- **Infrastructure**: Google Cloud Platform, Terraform

### Data Sources
- BigQuery tables: `fact_batting_stats_with_risp`, `fact_pitching_stats`
- MLB official statistics (2021-2024 seasons)
- Minimum sample size: 100 plate appearances

---

**Last Updated**: 2025-01-20
**Author**: Diamond Lens Project
**Contact**: GitHub Repository
