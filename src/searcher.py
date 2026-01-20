import arxiv
def search_papers(category="cs.AI", max_results=5):
    """
    指定したカテゴリから最新の論文オブジェクトのリストを返す
    """
    print(f"Searching for {max_results} papers in category: {category}...")
    client = arxiv.Client()
    search = arxiv.Search(
        query=f"cat:{category}",
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    # 後の処理で使いやすいようにリストにして返す
    return list(client.results(search))

if __name__ == "__main__":
    # テスト用：検索してタイトルだけ表示
    papers = search_papers("cs.AI", 3)
    for p in papers:
        print(f"- [{p.get_short_id()}] {p.title}")