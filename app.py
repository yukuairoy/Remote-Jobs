from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
import re
from collections import Counter
import json
import math

app = Flask(__name__)

# Load and process data
def load_job_data():
    """Load and standardize job data from all companies"""
    companies = {
        'mercor': {
            'file': 'tagged/mercor_jobs_tagged.csv',
            'map': {
                'title': 'title',
                'url': 'absolute_url',
                'description': 'description',
                'salary': 'compensation',
                'location': 'location',
                'tag_ids': 'tag_ids'
            }
        },
        'afterquery': {
            'file': 'tagged/afterquery_jobs_tagged.csv',
            'map': {
                'title': 'Position',
                'url': 'Detail URL',
                'description': 'Job Description',
                'salary': 'Salary Range',
                'location': None,  # Always remote
                'tag_ids': 'tag_ids'
            }
        },
        'alignerr': {
            'file': 'tagged/alignerr_jobs_tagged.csv',
            'map': {
                'title': 'title',
                'url': 'absolute_url',
                'description': 'description_raw',
                'salary': 'salary',
                'location': 'location',
                'tag_ids': 'tag_ids'
            }
        },
        'handshake': {
            'file': 'tagged/handshake_jobs_tagged.csv',
            'map': {
                'title': 'title',
                'url': 'url',
                'description': 'overview',
                'salary': 'pay',
                'location': None,  # Always remote
                'tag_ids': 'tag_ids'
            }
        },
        'outlier': {
            'file': 'tagged/outlier_jobs_tagged.csv',
            'map': {
                'title': 'title',
                'url': 'url',
                'description': 'description',
                'salary': 'payment',
                'location': 'location',
                'tag_ids': 'tag_ids'
            }
        },
        'invisible': {
            'file': 'tagged/invisible_jobs_tagged.csv',
            'map': {
                'title': 'title',
                'url': 'url',
                'description': 'description_raw',
                'salary': None,  # No salary column in invisible jobs
                'location': 'location',
                'tag_ids': 'tag_ids'
            }
        }
    }

    all_jobs = []
    for company, meta in companies.items():
        try:
            df = pd.read_csv(meta['file'])
            df.columns = [col.strip() for col in df.columns]  # Strip whitespace

            # Build a new DataFrame with the standard columns
            std = pd.DataFrame()
            for std_col, csv_col in meta['map'].items():
                if csv_col and csv_col in df.columns:
                    std[std_col] = df[csv_col]
                elif std_col == 'location' and company in ['afterquery', 'handshake']:
                    std[std_col] = 'Remote'
                else:
                    std[std_col] = None

            std['company'] = company
            all_jobs.append(std)
        except Exception as e:
            print(f"Error loading {company}: {e}")

    return pd.concat(all_jobs, ignore_index=True)

# Load tags mapping
def load_tags():
    """Load the tags mapping from the markdown file"""
    tags = {}
    try:
        with open('augment/Tags.md', 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.strip() and '. ' in line:
                    parts = line.strip().split('. ', 1)
                    if len(parts) == 2:
                        tag_id = int(parts[0])
                        tag_name = parts[1].strip()
                        tags[tag_id] = tag_name
    except:
        # Fallback tags if file not found
        tags = {
            1: "Math & Stats", 2: "Chemistry & Materials Science", 3: "Physics & Astronomy",
            4: "Biology & Life Sciences", 5: "Environmental Science", 6: "Mechanical & Industrial & Electrical Engineering",
            7: "Computer Programming & DevOps & Cloud & Data Infrastructure", 8: "AI Safety & Cybersecurity",
            9: "Game Development", 10: "Robotics", 11: "Finance, Accounting & Investment",
            12: "Insurance & Acturial", 13: "Real Estate", 14: "Legal & Compliance",
            15: "Supply Chain & Logistics", 16: "Strategy & Operations", 17: "Product & Project Management",
            18: "Sales & Marketing & Customer Success", 19: "Data Science & Machine Learning",
            20: "Medical & Clinical Practice", 21: "Creative & Digital Design", 22: "Social Sciences & Humanities",
            23: "Education", 24: "Human Resources & Talent Management", 25: "Writing, Language & Localization",
            26: "Nonprofit", 27: "Quality Assurance", 28: "None of the above categories"
        }
    return tags

# Extract salary information
def extract_salary_range(salary_str):
    """Extract numeric salary range from string"""
    if pd.isna(salary_str) or salary_str == 'Not specified':
        return None, None
    
    # Remove common text and extract numbers
    salary_str = str(salary_str).lower()
    
    # Handle different formats
    if 'hourly' in salary_str or '/hr' in salary_str:
        # Extract hourly rates
        numbers = re.findall(r'\$?(\d+(?:,\d+)?)', salary_str)
        if len(numbers) >= 2:
            return float(numbers[0].replace(',', '')), float(numbers[1].replace(',', ''))
        elif len(numbers) == 1:
            return float(numbers[0].replace(',', '')), float(numbers[0].replace(',', ''))
    
    # Handle ranges like "$30 - $60/hr"
    range_match = re.search(r'\$?(\d+(?:,\d+)?)\s*[-–]\s*\$?(\d+(?:,\d+)?)', salary_str)
    if range_match:
        return float(range_match.group(1).replace(',', '')), float(range_match.group(2).replace(',', ''))
    
    # Handle single values
    single_match = re.search(r'\$?(\d+(?:,\d+)?)', salary_str)
    if single_match:
        value = float(single_match.group(1).replace(',', ''))
        return value, value
    
    return None, None

# Parse tag IDs
def parse_tag_ids(tag_ids_str):
    """Parse tag IDs string into list of integers"""
    if pd.isna(tag_ids_str):
        return [28]  # Default to "None of the above"
    
    try:
        # Handle comma-separated values
        if ',' in str(tag_ids_str):
            return [int(x.strip()) for x in str(tag_ids_str).split(',') if x.strip().isdigit()]
        else:
            return [int(tag_ids_str)]
    except:
        return [28]

def calculate_similarity(job1_tags, job2_tags):
    """Calculate Jaccard similarity between two job tag sets"""
    if not job1_tags or not job2_tags:
        return 0.0
    
    set1 = set(job1_tags)
    set2 = set(job2_tags)
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0

# Load data
jobs_df = load_job_data()

# Generate unique IDs for each job
jobs_df['id'] = [f"job_{i:06d}" for i in range(len(jobs_df))]

tags_dict = load_tags()

# Process salary data
jobs_df['salary_min'], jobs_df['salary_max'] = zip(*jobs_df['salary'].apply(extract_salary_range))
jobs_df['salary_avg'] = jobs_df[['salary_min', 'salary_max']].mean(axis=1)

# Process tags
jobs_df['tag_list'] = jobs_df['tag_ids'].apply(parse_tag_ids)
jobs_df['tag_names'] = jobs_df['tag_list'].apply(lambda x: [tags_dict.get(tag_id, f"Unknown ({tag_id})") for tag_id in x])

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """Get overall statistics"""
    stats = {
        'total_jobs': len(jobs_df),
        'companies': {}
    }
    
    for company in jobs_df['company'].unique():
        company_jobs = jobs_df[jobs_df['company'] == company]
        company_stats = {
            'total_jobs': len(company_jobs),
            'avg_salary': company_jobs['salary_avg'].mean(),
            'salary_range': {
                'min': company_jobs['salary_min'].min(),
                'max': company_jobs['salary_max'].max()
            }
        }
        stats['companies'][company] = company_stats
    
    return jsonify(stats)

@app.route('/api/jobs')
def get_jobs():
    """Get jobs with filtering"""
    company = request.args.get('company', 'all')
    tag_filter = request.args.get('tag', 'all')
    search = request.args.get('search', '').lower()
    
    filtered_df = jobs_df.copy()
    
    # Filter by company
    if company != 'all':
        filtered_df = filtered_df[filtered_df['company'] == company]
    
    # Filter by tag
    if tag_filter != 'all':
        tag_id = int(tag_filter)
        filtered_df = filtered_df[filtered_df['tag_list'].apply(lambda x: tag_id in x)]
    
    # Filter by search
    if search:
        filtered_df = filtered_df[
            filtered_df['title'].str.lower().str.contains(search, na=False) |
            filtered_df['description'].str.lower().str.contains(search, na=False)
        ]
    
    # Convert to JSON-serializable format
    jobs_list = []
    for _, job in filtered_df.iterrows():
        # Handle NaN values for all fields
        def clean_value(value):
            if pd.isna(value) or (isinstance(value, float) and math.isnan(value)):
                return None
            return value
        
        job_dict = {
            'id': job['id'],  # Use the generated unique ID
            'title': clean_value(job.get('title', '')),
            'company': clean_value(job.get('company', '')),
            'location': clean_value(job.get('location', '')),
            'salary': clean_value(job.get('salary', '')),
            'salary_avg': clean_value(job.get('salary_avg')),
            'description': clean_value(job.get('description', ''))[:200] + '...' if len(str(clean_value(job.get('description', '')) or '')) > 200 else clean_value(job.get('description', '')),
            'tag_names': job.get('tag_names', []),
            'url': clean_value(job.get('absolute_url', job.get('Detail URL', job.get('url', ''))))
        }
        jobs_list.append(job_dict)
    
    return jsonify(jobs_list)

@app.route('/api/tags')
def get_tags():
    """Get all available tags"""
    return jsonify(tags_dict)

@app.route('/api/company-analysis')
def get_company_analysis():
    """Get detailed company analysis"""
    analysis = {}
    
    for company in jobs_df['company'].unique():
        company_jobs = jobs_df[jobs_df['company'] == company]
        
        # Salary analysis
        salary_data = company_jobs[company_jobs['salary_avg'].notna()]
        
        # Tag frequency
        all_tags = []
        for tags in company_jobs['tag_list']:
            all_tags.extend(tags)
        tag_counts = Counter(all_tags)
        
        # Top tags
        top_tags = [(tags_dict.get(tag_id, f"Unknown ({tag_id})"), count) 
                   for tag_id, count in tag_counts.most_common(10)]
        
        analysis[company] = {
            'total_jobs': len(company_jobs),
            'avg_salary': salary_data['salary_avg'].mean() if len(salary_data) > 0 else None,
            'salary_std': salary_data['salary_avg'].std() if len(salary_data) > 0 else None,
            'top_tags': top_tags,
            'salary_distribution': {
                'min': salary_data['salary_min'].min() if len(salary_data) > 0 else None,
                'max': salary_data['salary_max'].max() if len(salary_data) > 0 else None,
                'median': salary_data['salary_avg'].median() if len(salary_data) > 0 else None
            }
        }
    
    return jsonify(analysis)

@app.route('/api/mercor-competitiveness')
def get_mercor_competitiveness():
    """Get Mercor's competitiveness analysis"""
    mercor_jobs = jobs_df[jobs_df['company'] == 'mercor']
    competitors = jobs_df[jobs_df['company'] != 'mercor']
    
    # Salary comparison
    mercor_salaries = mercor_jobs[mercor_jobs['salary_avg'].notna()]['salary_avg']
    competitor_salaries = competitors[competitors['salary_avg'].notna()]['salary_avg']
    
    # Tag overlap analysis
    mercor_tags = set()
    for tags in mercor_jobs['tag_list']:
        mercor_tags.update(tags)
    
    competitor_tags = set()
    for tags in competitors['tag_list']:
        competitor_tags.update(tags)
    
    overlap_tags = mercor_tags.intersection(competitor_tags)
    unique_mercor_tags = mercor_tags - competitor_tags
    unique_competitor_tags = competitor_tags - mercor_tags
    
    return jsonify({
        'salary_comparison': {
            'mercor_avg': mercor_salaries.mean() if len(mercor_salaries) > 0 else None,
            'competitor_avg': competitor_salaries.mean() if len(competitor_salaries) > 0 else None,
            'mercor_median': mercor_salaries.median() if len(mercor_salaries) > 0 else None,
            'competitor_median': competitor_salaries.median() if len(competitor_salaries) > 0 else None
        },
        'tag_analysis': {
            'overlap_tags': [tags_dict.get(tag_id, f"Unknown ({tag_id})") for tag_id in overlap_tags],
            'unique_mercor_tags': [tags_dict.get(tag_id, f"Unknown ({tag_id})") for tag_id in unique_mercor_tags],
            'unique_competitor_tags': [tags_dict.get(tag_id, f"Unknown ({tag_id})") for tag_id in unique_competitor_tags]
        },
        'market_share': {
            'mercor_jobs': len(mercor_jobs),
            'total_jobs': len(jobs_df),
            'mercor_percentage': len(mercor_jobs) / len(jobs_df) * 100
        }
    })

@app.route('/api/similar-jobs/<job_id>')
def get_similar_jobs(job_id):
    """Find similar jobs from competitors using Jaccard similarity on tag IDs"""
    try:
        # Find the target job
        target_job = jobs_df[jobs_df['id'] == job_id]
        if target_job.empty:
            return jsonify({'error': 'Job not found'}), 404
        
        target_job = target_job.iloc[0]
        target_tags = target_job['tag_list']
        target_company = target_job['company']
        
        # Get all competitor jobs (jobs from other companies)
        competitor_jobs = jobs_df[jobs_df['company'] != target_company].copy()
        
        # Calculate Jaccard similarity for all competitor jobs
        competitor_jobs['similarity_score'] = competitor_jobs['tag_list'].apply(
            lambda x: calculate_similarity(target_tags, x) * 100
        )
        
        # Filter out jobs with 0 similarity (no tag overlap)
        competitor_jobs = competitor_jobs[competitor_jobs['similarity_score'] > 0]
        
        # Sort by similarity score (highest first) and take top 10
        competitor_jobs = competitor_jobs.sort_values('similarity_score', ascending=False).head(10)
        
        # Determine match type
        if len(competitor_jobs) > 0:
            top_similarity = competitor_jobs.iloc[0]['similarity_score']
            match_type = 'exact' if top_similarity == 100.0 else 'similar'
        else:
            match_type = 'none'
        
        # Prepare response
        similar_jobs = []
        for _, job in competitor_jobs.iterrows():
            # Skip jobs with no meaningful information
            title = job['title'] if pd.notna(job['title']) else None
            description = job['description'] if pd.notna(job['description']) else None
            salary = job['salary'] if pd.notna(job['salary']) else None
            
            # Skip jobs that have no title, no description, and no salary info
            if not title and not description and not salary:
                continue
                
            similar_jobs.append({
                'id': job['id'],  # Use the generated unique ID
                'title': title or 'Title not available',
                'company': job['company'] if pd.notna(job['company']) else 'Unknown',
                'location': job['location'] if pd.notna(job['location']) else 'Remote',
                'description': description or 'Description not available',
                'salary': salary or 'Salary not specified',
                'salary_avg': job['salary_avg'] if pd.notna(job['salary_avg']) else None,
                'url': job['url'] if pd.notna(job['url']) else None,
                'tag_names': job['tag_names'] if isinstance(job['tag_names'], list) and len(job['tag_names']) > 0 else ['No tags'],
                'similarity_score': round(job['similarity_score'], 1)
            })
        
        return jsonify({
            'target_job': {
                'id': target_job['id'],  # Use the generated unique ID
                'title': target_job['title'] if pd.notna(target_job['title']) else 'No title',
                'company': target_job['company'] if pd.notna(target_job['company']) else 'Unknown',
                'tag_names': target_job['tag_names'] if isinstance(target_job['tag_names'], list) and len(target_job['tag_names']) > 0 else ['No tags']
            },
            'similar_jobs': similar_jobs,
            'match_type': match_type
        })
        
    except Exception as e:
        print(f"Error in get_similar_jobs: {str(e)}")
        return jsonify({'error': 'Error loading similar jobs'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 