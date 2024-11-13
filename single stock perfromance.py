import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import yfinance as yf
import os
from datetime import datetime

# Prompting user to enter the ticker symbol
ticker_symbol = input("Please enter the ticker symbol: ")

# Calculate the end date as December 31 of the previous year
today = datetime.today()
last_day_of_previous_year = today.replace(year=today.year - 1, month=12, day=31)
end_date = last_day_of_previous_year.strftime('%Y-%m-%d')

# Specify the directory path
output_dir = r'C:\Users\HR\OneDrive\Desktop\Spring 24\Schaffer\'s investment\pic'
print(f"Saving images to: {output_dir}")

# Create the directory if it does not exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Download stock data for the entered ticker symbol
stock_data = yf.download(ticker_symbol, start='2010-01-01', end=end_date)

# Create a column for the month and year
stock_data['Month'] = stock_data.index.month
stock_data['Year'] = stock_data.index.year

# Calculate monthly returns
stock_data['Monthly Return'] = stock_data['Adj Close'].pct_change().groupby([stock_data['Year'], stock_data['Month']]).transform('sum')

# Remove incomplete months from the current year
complete_months = stock_data.groupby(['Year', 'Month']).size().unstack(fill_value=0)
last_year = last_day_of_previous_year.year
months_in_last_year = complete_months.loc[last_year]
months_to_exclude = months_in_last_year[months_in_last_year == 0].index
stock_data = stock_data[~((stock_data['Year'] == last_year) & (stock_data['Month'].isin(months_to_exclude)))]

# Pivot table to create the heatmap data
heatmap_data = stock_data.pivot_table(values='Monthly Return', index='Year', columns='Month', aggfunc=np.mean)

# Plotting the heatmap
plt.figure(figsize=(14, 8))
sns.heatmap(heatmap_data, cmap='RdYlGn', center=0, annot=True, fmt=".2%")
plt.title(f'Seasonality Heatmap for {ticker_symbol} Stock')
plt.xlabel('Month')
plt.ylabel('Year')
plt.xticks(ticks=np.arange(12) + 0.5, labels=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
plt.yticks(rotation=0)
plt.show()

# Calculating average monthly return and probability of positive returns
monthly_avg_return = heatmap_data.mean()
positive_return_prob = (heatmap_data > 0).mean()

# Combining the results into a DataFrame for better visualization
analysis_df = pd.DataFrame({
    'Average Return': monthly_avg_return,
    'Probability of Positive Return': positive_return_prob
})
print(analysis_df)

# Sorting and plotting the probability and average monthly returns
for metric, title, color in zip(
    ['Probability of Positive Return', 'Average Return'],
    ['Probability of Positive Returns by Month', 'Average Monthly Returns by Month'],
    ['skyblue', 'lightgreen']
):
    sorted_data = analysis_df[metric].sort_values()
    plt.figure(figsize=(10, 6))
    bars = sorted_data.plot(kind='bar', color=color)
    plt.title(f'{title} for {ticker_symbol} Stock')
    plt.xlabel('Month')
    plt.ylabel(metric)
    plt.xticks(ticks=np.arange(12), labels=sorted_data.index.map({1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}), rotation=45)
    plt.grid(axis='y')

    # Adding percentage labels on the bars
    for bar in bars.patches:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2., height, f'{height:.2%}', ha='center', va='bottom')

    plt.show()
