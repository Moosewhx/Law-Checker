const cityInput = document.getElementById('cityInput');
const statusDiv = document.getElementById('status');
const resultsDiv = document.getElementById('results');
const reportDiv = document.getElementById('report');
const linksDiv = document.getElementById('links');
const pdfsDiv = document.getElementById('pdfs');
const startButton = document.getElementById('startButton');

async function startAnalysis() {
    const city = cityInput.value.trim();
    if (!city) {
        alert('都市名を入力してください！');
        return;
    }

    startButton.disabled = true;
    statusDiv.textContent = '処理中です。関連リンクを検索・フィルタリングしています... 10-15分かかる場合があります。ページを閉じないでください。';
    statusDiv.style.color = 'blue';
    resultsDiv.style.display = 'none';

    // 创建一个AbortController来处理超时 - 延长到18分钟
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
        controller.abort();
    }, 1080000); // 18分钟超时 (1080秒)

    try {
        const response = await fetch('/api/run-analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ city: city }),
            signal: controller.signal  // 添加超时信号
        });

        clearTimeout(timeoutId); // 清除超时定时器

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ 
                detail: `サーバーエラー (HTTP ${response.status}): ${response.statusText}` 
            }));
            throw new Error(errorData.detail);
        }

        const data = await response.json();

        // 检查返回的数据结构
        if (!data || typeof data !== 'object') {
            throw new Error('サーバーから無効なデータが返されました');
        }

        statusDiv.textContent = `分析完了！${data.summary || '処理が完了しました'}`;
        statusDiv.style.color = 'green';
        resultsDiv.style.display = 'block';
        
        // 显示报告
        if (data.report) {
            reportDiv.innerHTML = markdownToHtml(data.report);
        } else {
            reportDiv.innerHTML = '<p>レポートデータがありません</p>';
        }
        
        // 显示相关链接
        if (data.relevant_links && data.relevant_links.length > 0) {
            let linksHtml = '<h3>関連性の高いリンク</h3><ul>';
            data.relevant_links.forEach((link, index) => {
                linksHtml += `<li>
                    <strong>${link.type || 'UNKNOWN'}</strong>: 
                    <a href="${link.url}" target="_blank" rel="noopener">${link.url}</a>
                    ${link.downloaded ? ` <span style="color: green;">[ダウンロード済み]</span>` : ''}
                </li>`;
            });
            linksHtml += '</ul>';
            linksDiv.innerHTML = linksHtml;
        } else {
            linksDiv.innerHTML = '<h3>関連リンクが見つかりませんでした</h3><p>AIフィルターの判定が厳しすぎる可能性があります。別の都市で試してみてください。</p>';
        }
        
        // 显示PDF下载链接
        if (data.pdf_downloads && data.pdf_downloads.length > 0) {
            let pdfsHtml = '<h3>ダウンロード済みPDFファイル</h3><ul>';
            data.pdf_downloads.forEach(pdf => {
                pdfsHtml += `<li>
                    <a href="${pdf.local_path}" target="_blank">${pdf.filename}</a>
                    <small> (元URL: <a href="${pdf.original_url}" target="_blank" rel="noopener">リンク</a>)</small>
                </li>`;
            });
            pdfsHtml += '</ul>';
            pdfsDiv.innerHTML = pdfsHtml;
        } else {
            pdfsDiv.innerHTML = '<h3>ダウンロードできたPDFファイルはありませんでした</h3>';
        }

        // 显示统计信息
        if (data.statistics) {
            const statsHtml = `
                <div style="background-color: #f0f8ff; padding: 1em; border-radius: 4px; margin-top: 1em;">
                    <h4>処理統計</h4>
                    <p>総クロール数: ${data.statistics.total_crawled || 0}件</p>
                    <p>処理対象数: ${data.statistics.processed_count || 0}件</p>
                    <p>関連リンク数: ${data.statistics.relevant_count || 0}件</p>
                    <p>PDF数: ${data.statistics.pdf_count || 0}件</p>
                </div>
            `;
            reportDiv.innerHTML += statsHtml;
        }

    } catch (error) {
        clearTimeout(timeoutId);
        
        let errorMessage = 'エラーが発生しました';
        
        if (error.name === 'AbortError') {
            errorMessage = 'タイムアウト: 処理に時間がかかりすぎました（18分超過）。サーバーが高負荷の可能性があります。';
        } else if (error.message) {
            errorMessage = `エラー: ${error.message}`;
        }
        
        statusDiv.textContent = errorMessage;
        statusDiv.style.color = 'red';
        
        // 显示错误详情
        resultsDiv.style.display = 'block';
        reportDiv.innerHTML = `
            <div style="background-color: #ffe6e6; padding: 1em; border-radius: 4px;">
                <h3>エラー詳細</h3>
                <p>${errorMessage}</p>
                <h4>対処方法:</h4>
                <ul>
                    <li>ページを再読み込みして再試行してください</li>
                    <li>別の都市名で試してみてください</li>
                    <li>時間を置いてから再度お試しください</li>
                    <li>問題が続く場合は、開発者コンソール（F12）でエラーを確認してください</li>
                </ul>
            </div>
        `;
        linksDiv.innerHTML = '';
        pdfsDiv.innerHTML = '';
        
        console.error('Analysis error:', error);
    } finally {
        startButton.disabled = false;
    }
}

function markdownToHtml(markdown) {
    if (!markdown || typeof markdown !== 'string') {
        return '<p>無効なマークダウンデータ</p>';
    }
    
    return markdown
        .replace(/^### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^# (.+)$/gm, '<h2>$1</h2>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
        .replace(/\n/g, '<br>');
}
