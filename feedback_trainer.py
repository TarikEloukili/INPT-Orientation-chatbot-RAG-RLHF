# Training script to learn from feedback
# feedback_trainer.py

import sqlite3
import json
import os
from dotenv import load_dotenv

def load_feedback_data():
    """Load feedback data from the database"""
    conn = sqlite3.connect('feedback.db')
    c = conn.cursor()
    
    # Get all feedback entries
    c.execute("SELECT * FROM feedback")
    feedback_data = c.fetchall()
    
    conn.close()
    
    # Format data for analysis
    formatted_data = []
    for data in feedback_data:
        formatted_data.append({
            'id': data[0],
            'query': data[1],
            'response': data[2],
            'feedback': data[3],
            'timestamp': data[4]
        })
    
    return formatted_data

def analyze_feedback():
    """Analyze feedback for patterns and insights"""
    data = load_feedback_data()
    
    # Get counts of likes and dislikes
    likes = sum(1 for item in data if item['feedback'] == 'like')
    dislikes = sum(1 for item in data if item['feedback'] == 'dislike')
    
    total = len(data)
    if total == 0:
        return {
            'stats': {
                'likes': 0,
                'dislikes': 0,
                'total': 0,
                'like_percentage': 0
            },
            'insights': [],
            'recommendations': []
        }
    
    like_percentage = (likes / total) * 100 if total > 0 else 0
    
    # Simple analysis of disliked responses
    disliked_responses = [item for item in data if item['feedback'] == 'dislike']
    disliked_queries = [item['query'] for item in disliked_responses]
    
    # Very simple insights and recommendations
    insights = []
    recommendations = []
    
    if dislikes > 0:
        insights.append(f"There are {dislikes} disliked responses that might need improvement.")
        recommendations.append("Consider reviewing the disliked responses for common issues.")
    
    if like_percentage > 80:
        insights.append(f"High satisfaction rate of {like_percentage:.1f}%")
        recommendations.append("System is performing well, continue monitoring.")
    elif like_percentage < 50 and total > 10:
        insights.append(f"Low satisfaction rate of {like_percentage:.1f}%")
        recommendations.append("Consider updating the RAG system or improving document retrieval.")
    
    return {
        'stats': {
            'likes': likes,
            'dislikes': dislikes,
            'total': total,
            'like_percentage': like_percentage
        },
        'insights': insights,
        'recommendations': recommendations,
        'disliked_queries': disliked_queries[:5]  # Show top 5 disliked queries
    }

def export_analysis(analysis):
    """Export analysis to a JSON file"""
    with open('feedback_analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2)
    print("Analysis exported to feedback_analysis.json")

def main():
    """Main function to run the analysis"""
    print("Starting feedback analysis...")
    analysis = analyze_feedback()
    
    print("\n=== Feedback Analysis ===")
    print(f"Total responses: {analysis['stats']['total']}")
    print(f"Likes: {analysis['stats']['likes']}")
    print(f"Dislikes: {analysis['stats']['dislikes']}")
    print(f"Satisfaction rate: {analysis['stats']['like_percentage']:.1f}%")
    
    print("\n=== Insights ===")
    for insight in analysis['insights']:
        print(f"- {insight}")
    
    print("\n=== Recommendations ===")
    for recommendation in analysis['recommendations']:
        print(f"- {recommendation}")
    
    if 'disliked_queries' in analysis and analysis['disliked_queries']:
        print("\n=== Sample Disliked Queries ===")
        for query in analysis['disliked_queries']:
            print(f"- {query}")
    
    export_analysis(analysis)

if __name__ == "__main__":
    load_dotenv()
    main()