# Audit Output Dashboard

The CIP/CDD Audit Risk Assessment dashboard is an interactive Streamlit experience that helps assurance teams understand the status of Customer Identification Program (CIP) and Customer Due Diligence (CDD) controls. It loads the latest questionnaire results, computes summary metrics, and presents the data through linked visualisations:

- Executive view of overall compliance, category performance, and record-level detail.
- Gap analysis with heat maps, Sankey flows, priority bubbles, and a control-level waterfall that quantify the cumulative deficit.
- Remediation planning workspace that plots timelines, models remediation scenarios, and surfaces high-risk requirements.

Explore the live deployment here: https://audit---output-dashboard-demo.streamlit.app/

## Getting started

1. Create and activate a Python 3.10+ environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
3. Generate the CSV dataset (only required after updating the Excel workbook):

   ```bash
   python scripts/convert_excel_to_csv.py
   ```
4. Launch the Streamlit app:

   ```bash
   streamlit run app.py
   ```

## Project structure

- `scripts/convert_excel_to_csv.py` - converts the Excel source into a cleaned CSV used by the dashboard.
- `data/compliance_dashboard_data.csv` - pre-generated dataset powering the app.
- `data_manager.py` - data access helpers and filter utilities.
- `charts.py` - Plotly chart builders for each dashboard component.
- `app.py` - Streamlit UI with multi-page navigation and interactive controls.

## Regenerating data

If the questionnaire workbook changes, rerun the conversion script to refresh the CSV before restarting the app.

## Committing your changes

To save your local modifications back to this repository:

1. Review which files have been modified:

   ```bash
   git status
   ```

2. Stage the files you want to include in the commit (replace the example paths with the files you changed):

   ```bash
   git add app.py data_manager.py
   ```

3. Create the commit with a descriptive message:

   ```bash
   git commit -m "Describe the change you made"
   ```

4. (Optional) If this is your first commit on this machine, configure your Git identity so the commit is attributed to you:

   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```

5. Push the commit to the remote repository:
4. Push the commit to the remote repository:

   ```bash
   git push origin work
   ```

If you are working on a different branch, replace `work` with your branch name in the push command.

If Git reports that the branch has no upstream set, run `git push -u origin work` once so future `git push` commands can omit the branch name.
