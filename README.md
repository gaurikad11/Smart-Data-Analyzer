# 📊 Smart Data Analyzer


<p align="center">
  <b>An AI-powered web application for automated CSV data analysis, cleaning, visualization, and intelligent business insights.</b>
</p>

---

## 📌 Overview

**Smart Data Analyzer** is an AI-powered data analytics application that enables users to upload CSV datasets and perform comprehensive exploratory data analysis without writing a single line of code.

The application automatically profiles datasets, cleans missing values and duplicates, generates interactive visualizations, and leverages **Llama 3.1 (via Groq API)** to provide business insights and answer natural language questions about the uploaded data.

---

## ✨ Features

- 📁 Upload and analyze any CSV dataset
- 🔍 Automatic dataset profiling
- 📊 Statistical summary generation
- 🧹 One-click data cleaning
  - Handle missing values
  - Remove duplicate records
- 📈 Interactive visualizations
  - Bar Chart
  - Line Chart
  - Scatter Plot
  - Histogram
  - Box Plot
  - Pie Chart
  - Correlation Heatmap
- 🤖 AI-generated business insights using **Llama 3.1**
- 💬 Ask questions about your dataset in natural language
- 📥 Download the cleaned dataset
- ⚡ Fast and interactive Streamlit interface

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.12 |
| Frontend | Streamlit, HTML, CSS |
| Data Processing | Pandas, NumPy |
| Visualization | Plotly Express |
| AI Model | Llama 3.1 (8B) |
| API | Groq API |
| Environment | python-dotenv |

---

## 🚀 Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/gaurikad11/Smart-Data-Analyzer.git

cd Smart-Data-Analyzer
```

---

### 2️⃣ Create a Virtual Environment

```bash
python -m venv venv
```

---

### 3️⃣ Activate the Environment

#### Windows

```bash
venv\Scripts\activate
```

#### Linux/macOS

```bash
source venv/bin/activate
```

---

### 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 5️⃣ Configure Environment Variables

Create a `.env` file in the project root and add your Groq API key.

```env
GROQ_API_KEY=your_groq_api_key_here
```

---

### 6️⃣ Run the Application

```bash
streamlit run app.py
```

---

## 📊 Workflow

```text
Upload CSV
     │
     ▼
Automatic Data Profiling
     │
     ▼
Data Cleaning
     │
     ▼
Interactive Visualizations
     │
     ▼
AI-Powered Insights
     │
     ▼
Ask Questions About Data
     │
     ▼
Download Clean Dataset
```

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a new branch

```bash
git checkout -b feature-name
```

3. Commit your changes

```bash
git commit -m "Add new feature"
```

4. Push to GitHub

```bash
git push origin feature-name
```

5. Open a Pull Request

---

## 👩‍💻 Author

**Gauri Kad**

🎓 B.Tech CSE (AI & ML)

GitHub:
> https://github.com/gaurikad11

---

## ⭐ Support

If you found this project useful, please consider giving it a ⭐ on GitHub.

---

<p align="center">
Made with ❤️ using Python, Streamlit, Plotly & Llama 3.1
</p>
