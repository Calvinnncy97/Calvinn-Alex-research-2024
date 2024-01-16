import duckdb


conn = duckdb.connect()
df = conn.execute(
    
    '''
    Select concat_ws('\n',
        concat_ws(':', 'Question', question), 
        concat_ws(':', 'Answer', answer)
) as qa
    from read_parquet('/home/alextay96/Desktop/workspace/boson/unified-scraping-framework/output/qa/*.parquet')
    '''
).df()
qa_list = df["qa"].tolist()[:1000]
text = "\n\n".join(qa_list)
with open('quora_qa_dataset_sample.txt', 'w') as f:
    f.write(text)
