## 📊 Exploratory Data Analysis (EDA)

- Transaction Amount by Fraud
- Transaction Type vs Fraud
- Correlation Matrix
- Fraud by High-Amount Flag
- Distribution of Amounts by Type

---

## 🤖 Model Training

- Models Used: Logistic Regression, XGBoost (best)
- Handling Imbalance: `scale_pos_weight`, Stratified Split
- Final Model: **XGBoost** with high precision, recall, and AUC

---

## 🧠 Feature Engineering

- Transaction flags: `isHighAmount`, `dest_multiple_fraud`
- Behavioral signals: `origin_diff`, `sent_all_money`
- Encoded transaction types (CASH_OUT, TRANSFER, etc.)

---

## 📈 Model Insights

- Feature importance visualization (Top 15)
- Precision vs. Recall curve for threshold tuning
- Achieved ~100% recall and 99.9% accuracy on test set

---

## 📁 Dataset

> Due to file size and privacy, the CSV dataset is not included.  
> Please place `your_data.csv` manually in the root folder if you wish to rerun the notebook.

---

## 👨‍💻 Author

**Agathamudi Mahesh**  
📧 maheshagathamudi@gmail.com  
🔗 [LinkedIn](https://www.linkedin.com/in/maheshagathamudi/) | [GitHub](https://github.com/Maheshagathamudi)