# Improving RAG System Quality

## Changes Made

1. **Added Skill Training Guide Pages**: Updated `scrape_wiki.py` to automatically include all 23 skill pages and their training guides (e.g., "Attack/Guide", "Strength/Guide", etc.)

2. **Improved Retrieval Settings**: 
   - Increased `top_k` from 5 to 8 chunks for better coverage
   - Lowered `similarity_threshold` from 0.3 to 0.2 to get more relevant results

3. **Query Expansion**: Added automatic query expansion in `rag_system.py` to improve retrieval for training-related queries

## Next Steps to Improve Quality

To apply these improvements, you need to:

1. **Re-scrape with new pages**:
   ```bash
   python scrape_wiki.py
   ```
   This will add the skill training guide pages.

2. **Re-process the data**:
   ```bash
   python process_data.py
   ```

3. **Rebuild the vector database**:
   ```bash
   python create_vector_db.py --clear
   ```

4. **Test the improved system**:
   ```bash
   python cli_interface.py
   ```
   Then try: "can you give training guide info on the attack skill?"

## Additional Improvements You Can Try

- **Increase max_pages in config.yaml** to get more comprehensive coverage
- **Fine-tune similarity_threshold** based on your results (higher = stricter, lower = more results)
- **Adjust chunk_size** in config.yaml if chunks are too small/large
- **Try different embedding models** (see README for options)

