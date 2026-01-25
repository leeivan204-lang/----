function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.tryLock(10000);
  
  try {
    var doc = SpreadsheetApp.getActiveSpreadsheet();
    var data = JSON.parse(e.postData.contents);
    
    // 使用 user_id 作為分頁名稱，若無則預設 'Log'
    var sheetName = data.user_id || 'Log';
    var sheet = doc.getSheetByName(sheetName);
    
    // 如果分頁不存在則建立
    if (!sheet) {
      sheet = doc.insertSheet(sheetName);
      // 建立標題列: 日期、星期、身份、事件類別、事件名稱、說明、上傳檔案或網址(縮圖)、SystemID
      sheet.appendRow(['日期 (Date)', '星期 (Day)', '身份 (Role)', '事件類別 (Category)', '事件名稱 (Title)', '說明 (Description)', '檔案/網址 (File/Link)', 'SystemID']);
      sheet.setFrozenRows(1);
      sheet.hideColumns(8); // Hide SystemID
    }
    
    // 計算星期 (Day of Week)
    var d = new Date(data.date);
    var days = ['日', '一', '二', '三', '四', '五', '六'];
    var dayStr = days[d.getDay()];
    
    // IMAGE/FILE HANDLER
    // Expect: data.file_content (Base64), data.file_name, data.mime_type
    var fileUrl = "";
    if (data.file_content && data.file_name) {
       try {
         var folderName = "WorkLog_Uploads";
         var folders = DriveApp.getFoldersByName(folderName);
         var folder;
         if (folders.hasNext()) {
           folder = folders.next();
         } else {
           folder = DriveApp.createFolder(folderName);
         }
         
         var decoded = Utilities.base64Decode(data.file_content);
         var blob = Utilities.newBlob(decoded, data.mime_type || "application/octet-stream", data.file_name);
         var file = folder.createFile(blob);
         file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
         fileUrl = file.getUrl();
         
         // Override/Append to link field?
         // If multiple files, we might need a list. For now, let's treat 'link' as the primary cloud link.
         // Or append to 'file_names' column as a URL?
         // Let's prepend the Drive Link to the content or just set it as 'link' if empty.
         if(!data.link) {
            data.link = fileUrl;
         } else {
            // If link exists, maybe append to desc?
             data.desc = (data.desc || "") + "\n[File]: " + fileUrl;
         }
         
       } catch (e) {
         // return error or continue
         data.desc = (data.desc || "") + "\n[Upload Error]: " + e.toString();
       }
    }

    // 處理檔案/連結
    var contentParts = [];
    
    // 1. Link (Now includes Drive Link)
    if (data.link) {
      if (data.link.match(/\.(jpeg|jpg|gif|png)$/i)) {
          contentParts.push('=IMAGE("' + data.link + '")');
      } else {
          contentParts.push(data.link);
      }
    }
    
    // 2. Files
    if (data.file_names) {
      contentParts.push(data.file_names);
    }
    
    var content = contentParts.join("\n");
    
    var rowData = [
      "'" + data.date, 
      dayStr,
      data.role || "", 
      data.category || "",
      data.title,
      data.desc,
      content,
      data.id // System ID (Column H)
    ];

    // ACTION HANDLER
    if (data.action === "delete") {
       var rows = sheet.getDataRange().getValues();
       for (var i = 1; i < rows.length; i++) {
         // Check Column H (Index 7) for ID
         if (rows[i][7] == data.id) {
           sheet.deleteRow(i + 1);
           return ContentService.createTextOutput(JSON.stringify({"result":"deleted"})).setMimeType(ContentService.MimeType.JSON);
         }
       }
       return ContentService.createTextOutput(JSON.stringify({"result":"not_found"})).setMimeType(ContentService.MimeType.JSON);
       
    } else if (data.action === "update") {
       var rows = sheet.getDataRange().getValues();
       for (var i = 1; i < rows.length; i++) {
         if (rows[i][7] == data.id) {
           sheet.getRange(i + 1, 1, 1, 8).setValues([rowData]);
           return ContentService.createTextOutput(JSON.stringify({"result":"updated"})).setMimeType(ContentService.MimeType.JSON);
         }
       }
       // If not found, append? Or error? Let's append to be safe.
       sheet.appendRow(rowData);
       
    } else {
       // Default: Create
       sheet.appendRow(rowData);
    }
    
    return ContentService.createTextOutput(JSON.stringify({"result":"success", "row": sheet.getLastRow()})).setMimeType(ContentService.MimeType.JSON);
    
  } catch (e) {
    return ContentService.createTextOutput(JSON.stringify({"result":"error", "error": e})).setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

function setup() {
  var doc = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = doc.getSheetByName('Log');
  if (!sheet) {
    doc.insertSheet('Log');
    doc.getRange('A1:K1').setValues([['ID', 'Date', 'Role', 'Title', 'Description', 'Link', 'Notes', 'Category', 'User', 'WorkspaceID', 'Created At']]);
  }
}
