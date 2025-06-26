# Mercor Job Market Analysis

A comprehensive web application for browsing and analyzing job listings from Mercor and its competitors in the AI training job market.

## Overview

This application provides a simplified interface for:
- **All Jobs**: Browse and filter job listings from all companies (Mercor, AfterQuery, Alignerr, Handshake, Outlier)
- **Mercor Jobs**: Focus on Mercor's job listings with similar job matching functionality
- **Similar Jobs**: Find matching jobs from competitors using Jaccard similarity on skill tags

## Features

### 📋 All Jobs Browser
- Browse job listings from all 5 companies
- Filter by company, skill category, and search terms
- View job details, salaries, and requirements
- Direct links to job applications
- Pagination for easy navigation

### 💼 Mercor Jobs Browser
- Focused view of Mercor's job listings
- Filter by skill categories (28 different skill areas)
- Search functionality
- **Find Similar Jobs**: Click "Find Similar" to discover matching jobs from competitors with similarity scores
- Pagination support

### 🔍 Similar Jobs Feature
- **Jaccard Similarity Algorithm**: Finds jobs with overlapping skill requirements
- **Exact Matches**: Jobs with identical skill tags (100% similarity)
- **Partial Matches**: Jobs with some skill overlap (50%+ similarity)
- **Competitive Insights**: Compare Mercor's compensation and requirements vs competitors

## Data Sources

The application uses job data from 5 companies stored in CSV files:
- `tagged/mercor_jobs_tagged.csv` - Mercor jobs
- `tagged/afterquery_jobs_tagged.csv` - AfterQuery jobs  
- `tagged/alignerr_jobs_tagged.csv` - Alignerr jobs
- `tagged/handshake_jobs_tagged.csv` - Handshake jobs
- `tagged/outlier_jobs_tagged.csv` - Outlier jobs

Each CSV contains job details including title, description, salary, location, and skill tags.

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd human_data_jobs
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the application**
   - Open your browser and go to `http://localhost:5001`
   - The application will load with the "All Jobs" tab active

## Usage

### Browsing All Jobs
1. Navigate to the "All Jobs" tab
2. Use the filters on the left to:
   - Select a specific company
   - Filter by skill category
   - Search for specific terms
3. Browse through job listings with pagination
4. Click "View Job" to apply directly

### Exploring Mercor Jobs
1. Click on the "Mercor Jobs" tab
2. Use filters to narrow down by skills or search terms
3. For any Mercor job, click "Find Similar" to see matching competitor jobs
4. Compare salaries and skill requirements

### Finding Similar Jobs
1. From any Mercor job listing, click the green "Find Similar" button
2. A modal will open showing:
   - Target job details and skills
   - Similar jobs from competitors with similarity scores
   - Salary comparisons
   - Direct links to competitor jobs

## API Endpoints

### `/api/jobs`
Get job listings with optional filtering:
- `company`: Filter by company (mercor, afterquery, alignerr, handshake, outlier)
- `tag`: Filter by skill tag ID
- `search`: Search in job titles and descriptions

### `/api/tags`
Get all available skill categories (28 tags)

### `/api/similar-jobs/<job_id>`
Find similar jobs from competitors for a specific job:
- Returns up to 10 most similar jobs from other companies
- Includes similarity scores (0-100%)
- Shows job details, salaries, and skill matches
- Uses Jaccard similarity algorithm

## Technical Architecture

- **Backend**: Flask web framework with pandas for data processing
- **Frontend**: Bootstrap 5 with vanilla JavaScript
- **Data Processing**: Pandas for CSV handling and data manipulation
- **Similarity Algorithm**: Jaccard similarity on skill tag overlap
- **Pagination**: Client-side pagination for smooth user experience

## Similarity Algorithm

The application uses **Jaccard similarity** to find similar jobs:

**Formula**: `|A ∩ B| / |A ∪ B|`
- A = Skill tags of target job
- B = Skill tags of competitor job
- Result = Similarity score (0-100%)

**Example**:
- Target job: ["Finance", "Data Science"] 
- Competitor job: ["Finance"]
- Similarity: 1/(1+1) = 50%

## Customization

### Adding New Companies
1. Add CSV file to `tagged/` directory
2. Update the `companies` dictionary in `app.py`
3. Ensure consistent column names

### Modifying Skill Tags
1. Edit `augment/Tags.md` to add/remove skill categories
2. Update job CSV files with new tag IDs
3. Restart the application

### Styling Changes
- Modify `static/css/style.css` for visual changes
- Update `templates/index.html` for layout changes

## Future Enhancements

- **Advanced Filtering**: Salary range, location, job type filters
- **Saved Searches**: User accounts with saved job searches
- **Email Alerts**: Notifications for new similar jobs
- **Export Features**: Download job lists as CSV/PDF
- **Mobile App**: Native mobile application
- **Analytics Dashboard**: Detailed market analysis charts

## Troubleshooting

### Common Issues

1. **Port already in use**
   - Change port in `app.py`: `app.run(port=5002)`
   - Or kill existing process: `pkill -f "python app.py"`

2. **CSV loading errors**
   - Check file paths in `tagged/` directory
   - Verify CSV column names match expected format

3. **Similar jobs not working**
   - Ensure job IDs exist in CSV files
   - Check that tag IDs are properly formatted

### Debug Mode
The application runs in debug mode by default. Check the terminal for detailed error messages.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or issues, please open an issue in the repository or contact the development team.

---

**Built for competitive intelligence in the AI training market** 🤖📊 