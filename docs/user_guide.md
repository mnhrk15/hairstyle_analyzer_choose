# User Guide

This guide explains how to use the Hairstyle Analyzer application to analyze hairstyle images and generate formatted Excel output.

## Installation

1. Make sure you have Python 3.9 or higher installed on your system.

2. Install the application using the setup scripts:

   **Windows:**
   ```
   setup_env.bat
   ```

   **macOS/Linux:**
   ```
   chmod +x setup_env.sh
   ./setup_env.sh
   ```

3. Get a Gemini API key from Google AI Studio (https://aistudio.google.com/).

## Configuration

Before running the application, you need to:

1. Create a `.env` file in the project root directory with your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

2. Ensure you have a template CSV file. A default template is provided in `assets/templates/`.

## Starting the Application

1. Activate the virtual environment:

   **Windows:**
   ```
   venv\Scripts\activate
   ```

   **macOS/Linux:**
   ```
   source venv/bin/activate
   ```

2. Start the Streamlit application:
   ```
   streamlit run hairstyle_analyzer/ui/streamlit_app.py
   ```

3. Your default web browser should open automatically. If not, open it manually and navigate to the URL displayed in the terminal (usually http://localhost:8501).

## Using the Application

### Main Interface

The application has a main interface with:
- Image upload section
- Preview area
- Process button
- Results display
- Excel download button

### Step 1: Configure the Application

1. In the sidebar, enter your Gemini API key (if not already configured in `.env`).
2. Enter the HotPepper Beauty URL for your salon.
3. Adjust any other settings as needed.
4. Click the "Save Settings" button.

### Step 2: Upload Images

There are two ways to provide images:
1. Drag and drop image files onto the upload area
2. Click the "Browse files" button to select images

The application accepts PNG, JPG, and JPEG files.

### Step 3: Process Images

1. After uploading images, they will appear in the preview area.
2. Click the "Generate Titles" button to start processing.
3. The progress bar will show the status of the operation.

### Step 4: View Results

1. After processing is complete, results will be displayed in a table.
2. You can:
   - Sort the table by clicking column headers
   - Filter results using the search box
   - Expand rows to see detailed information

### Step 5: Download Excel File

1. Click the "Download Excel" button to download the results in Excel format.
2. The Excel file will contain the following columns:
   - スタイリスト名 (Stylist Name)
   - クーポン名 (Coupon Name)
   - コメント (Comment)
   - スタイルタイトル (Style Title)
   - 性別 (Gender)
   - 長さ (Length)
   - スタイルメニュー (Style Menu)
   - ハッシュタグ (Hashtags)
   - 画像ファイル名 (Image Filename)

## Template File Format

The template CSV file has the following columns:

| Column     | Description |
|------------|-------------|
| category   | Style category name (e.g., Latest Trend, Hair Quality Improvement, Short Bob) |
| title      | Style title |
| menu       | Style menu (e.g., Cut+Color, Treatment/Straightening) |
| comment    | Comments about the style (product description, selling points, target audience) |
| hashtag    | Style-related hashtags (comma-separated) |

## Troubleshooting

### Common Issues

1. **API Key Error**
   - Make sure your Gemini API key is correctly entered in the sidebar or `.env` file.
   - Verify the API key is active and hasn't reached its usage limits.

2. **Image Processing Error**
   - Ensure images are in a supported format (PNG, JPG, JPEG).
   - Check that the images are not corrupted.

3. **Web Scraping Error**
   - Verify the HotPepper Beauty URL is correct.
   - The salon page may have changed structure. Try again later or contact support.

4. **Excel Download Error**
   - Check that you have write permissions for the download location.
   - Make sure no other program is using the Excel file.

### Getting Help

If you encounter any issues not covered in this guide, please:
1. Check the logs in the `logs/` directory for detailed error information.
2. Contact support at support@example.com with a description of the issue.
