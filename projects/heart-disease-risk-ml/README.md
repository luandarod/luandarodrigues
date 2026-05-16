# Heart Disease Risk Prediction with Machine Learning

**Health Analytics | Machine Learning | Clinical Risk Factors | Model Evaluation**

This project analyzes a clinical heart disease dataset with 918 observations and 11 predictive variables to identify patterns associated with heart disease and compare classification models.

The project is designed as a portfolio case. It is not a diagnostic tool and should not be used for clinical decision-making without external validation, medical oversight and proper governance.

## Analytical question

How can structured clinical variables support exploratory risk stratification for heart disease, and what are the limits of this type of dataset when compared with current cardiovascular risk factors?

## Dataset

The dataset includes age, sex, chest pain type, resting blood pressure, cholesterol, fasting blood sugar, resting ECG, maximum heart rate, exercise-induced angina, Oldpeak / ST depression, ST slope and the heart disease target variable.

## Dataset overview

| Metric | Value |
|---|---:|
| Records | 918 |
| Columns | 12 |
| Predictive variables | 11 |
| Target prevalence | 55.3% |
| Missing values | 0 |
| Duplicates | 0 |
| Cholesterol values equal to zero | 172 |
| RestingBP values equal to zero | 1 |

## Model results

| Model | Accuracy | ROC-AUC | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.897 | 0.930 | 0.888 | 0.931 | 0.909 |
| Random Forest | 0.897 | 0.932 | 0.881 | 0.941 | 0.910 |

## Most relevant variables

Permutation importance suggested the strongest signals were ST_Slope, ChestPainType, Sex, ExerciseAngina, Cholesterol, Oldpeak, FastingBS and RestingBP.

## Clinical pattern examples

| Variable | Group | Heart disease rate |
|---|---|---:|
| ST_Slope | Flat | 82.8% |
| ST_Slope | Down | 77.8% |
| ST_Slope | Up | 19.7% |
| ChestPainType | ASY | 79.0% |
| ExerciseAngina | Yes | 85.2% |
| ExerciseAngina | No | 35.1% |

## Connection with current cardiovascular risk factors

The dataset covers several important cardiovascular risk dimensions, including age, sex, blood pressure, cholesterol, fasting blood sugar and stress-test/ECG signals.

However, it does not include several relevant factors used in current cardiovascular prevention discussions, such as smoking, BMI, physical activity, diet, sleep health, family history, medication use, kidney disease, socioeconomic determinants and access-to-care context.

## Methodology

1. Data quality review
2. Exploratory analysis by target variable
3. Encoding of categorical variables
4. Train/test split
5. Logistic Regression baseline
6. Random Forest model
7. Model evaluation with accuracy, ROC-AUC, precision, recall and F1
8. Permutation importance for interpretability
9. Clinical limitation analysis

## Tools

Python, Pandas, Scikit-learn, Matplotlib, Machine Learning, Classification, EDA, Model Evaluation, Health Analytics.

## Ethical and clinical limitations

This model does not replace medical evaluation. It was trained on a historical combined dataset and requires external validation before any operational use. In a real health setting, performance, bias, interpretability, privacy and clinical safety would need formal review.
