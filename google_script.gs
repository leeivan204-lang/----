function doGet(e) {
  var lock = LockService.getScriptLock();
  lock.tryLock(10000);
  
  try {
    var action = e.parameter.action;
    var doc = SpreadsheetApp.getActiveSpreadsheet();
    
    if (action === "login") {
       return handleLogin(e);
    } else if (action === "get_logs") {
       return handleGetLogs(e);
    }
    
    return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": "Unknown action"})).setMimeType(ContentService.MimeType.JSON);
    
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": err.toString()})).setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.tryLock(10000);
  
  try {
    var data = JSON.parse(e.postData.contents);
    var action = data.action;
    
    if (action === "create_log") {
      return handleCreateLog(data);
    } else if (action === "update_log") {
      return handleUpdateLog(data);
    } else if (action === "delete_log") {
      return handleDeleteLog(data);
    } else if (action === "create_user") {
      return handleCreateUser(data);
    }
    
    return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": "Unknown action"})).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": err.toString()})).setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

// --- Handlers ---

function handleLogin(e) {
  var username = e.parameter.username;
  var password = e.parameter.password; // Plain text sent from client (Simple HTTPS security)
  
  var sheet = getSheet("Users");
  var rows = sheet.getDataRange().getValues();
  
  for (var i = 1; i < rows.length; i++) {
    if (rows[i][0] == username) {
      // Check password (In real world, use hash. Here strictly matching or assume client sends hash)
      // Let's assume client sends plain pwd and we compare with plain for GAS simplicity or hash matched.
      // To strictly follow Python logic which used bcrypt, we can't easily do verify in GAS without libraries.
      // Compromise: We will trust the Client if it sends a specific "login_check" or we store plain for this demo?
      // BETTER: Apps Script is the backend. Let's store simple password or Client Hashed password.
      // Assumption: Client sends simple password.
      
      if (rows[i][1] == password) { // Column B is Password
         var role = rows[i][2]; // Column C is Role
         var token = Utilities.base64Encode(username + ":" + new Date().getTime());
         return jsonResp({
           "status": "success", 
           "access_token": token, 
           "user": {"username": username, "role": role} 
         });
      } else {
         return jsonResp({"status": "error", "message": "Invalid credentials"});
      }
    }
  }
  return jsonResp({"status": "error", "message": "User not found"});
}

function handleGetLogs(e) {
  // Return all logs from all sheets or specific logic?
  // Let's stick to "Log" sheet for simplicity as per original design
  var sheet = getSheet("Log");
  var rows = sheet.getDataRange().getValues();
  var logs = [];
  
  // Headers: ID, Date, Role, Title, Desc, Link, Notes, Category, User, WorkspaceID, Files
  // Index:   0   1     2     3      4     5     6      7         8     9            10
  // Note: Data structure in Sheet might have changed. Let's Standardize.
  // Standard Headers: [ID, Date, Role, Title, Desc, Link, Notes, Category, User, WorkspaceID, FileNames]
  
  for (var i = 1; i < rows.length; i++) {
    var r = rows[i];
    // Skip empty id
    if (!r[0]) continue;
    
    logs.push({
      "id": r[0],
      "date": formatDate(r[1]),
      "role": r[2],
      "title": r[3],
      "desc": r[4],
      "link": r[5],
      "notes": r[6],
      "category": r[7],
      "user_id": r[8],
      "workspace_id": r[9],
      "file_names": r[10]
    });
  }
  
  return jsonResp(logs);
}

function handleCreateLog(data) {
  var sheet = getSheet("Log");
  var id = new Date().getTime(); // Simple ID
  
  var fileNames = "";
  // Handle File Upload
  if (data.file_content && data.file_name) {
      fileNames = saveFileToDrive(data.file_content, data.file_name, data.mime_type);
  }
  
  // Append Row
  // Order: [ID, Date, Role, Title, Desc, Link, Notes, Category, User, WorkspaceID, FileNames]
  sheet.appendRow([
    id, 
    data.date, 
    data.role, 
    data.title, 
    data.desc, 
    data.link, 
    data.notes, 
    data.category, 
    data.user_id, 
    1, // Default workspace
    fileNames 
  ]);
  
  return jsonResp({"status": "success", "id": id, "file_names": fileNames});
}

function handleUpdateLog(data) {
  var sheet = getSheet("Log");
  var rows = sheet.getDataRange().getValues();
  var updated = false;
  
  for (var i = 1; i < rows.length; i++) {
    if (rows[i][0] == data.id) {
       // Found. Update columns.
       var rowNum = i + 1;
       
       // Handle New File
       var currentFiles = rows[i][10] || "";
       if (data.file_content && data.file_name) {
          var newFileLink = saveFileToDrive(data.file_content, data.file_name, data.mime_type);
          if (currentFiles) currentFiles += ",";
          currentFiles += newFileLink;
       }
       
       // Update Range: Columns 2(B)-11(K) -> Date to FileNames
       // Indices in row array: 1..10
       // Sheet setup: A=ID, B=Date ...
       
       sheet.getRange(rowNum, 2).setValue(data.date);
       sheet.getRange(rowNum, 3).setValue(data.role);
       sheet.getRange(rowNum, 4).setValue(data.title);
       sheet.getRange(rowNum, 5).setValue(data.desc);
       sheet.getRange(rowNum, 6).setValue(data.link);
       sheet.getRange(rowNum, 7).setValue(data.notes);
       sheet.getRange(rowNum, 8).setValue(data.category);
       // User ID (8) usually doesn't change
       // Workspace (9)
       sheet.getRange(rowNum, 11).setValue(currentFiles);
       
       updated = true;
       break;
    }
  }
  
  if (!updated) return jsonResp({"status": "error", "message": "Log not found"});
  return jsonResp({"status": "success"});
}

function handleDeleteLog(data) {
  var sheet = getSheet("Log");
  var rows = sheet.getDataRange().getValues();
  for (var i = 1; i < rows.length; i++) {
    if (rows[i][0] == data.id) {
      sheet.deleteRow(i + 1);
      return jsonResp({"status": "success"});
    }
  }
  return jsonResp({"status": "error", "message": "Log not found"});
}

function handleCreateUser(data) {
  var sheet = getSheet("Users");
  var rows = sheet.getDataRange().getValues();
  for (var i = 1; i < rows.length; i++) {
    if (rows[i][0] == data.username) {
       return jsonResp({"status": "error", "message": "User exists"});
    }
  }
  
  sheet.appendRow([data.username, data.password, data.role || "user", new Date()]);
  return jsonResp({"status": "success"});
}

// --- Helpers ---

function getSheet(name) {
  var doc = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = doc.getSheetByName(name);
  if (!sheet) {
    sheet = doc.insertSheet(name);
    if (name === "Log") {
       sheet.appendRow(['ID', 'Date', 'Role', 'Title', 'Desc', 'Link', 'Notes', 'Category', 'User', 'WorkspaceID', 'FileNames']);
    } else if (name === "Users") {
       sheet.appendRow(['Username', 'Password', 'Role', 'Created At']);
       // Default Admin
       sheet.appendRow(['admin', 'admin', 'admin', new Date()]);
    }
  }
  return sheet;
}

function saveFileToDrive(base64, name, mime) {
  try {
    var folderName = "WorkLog_Uploads";
    var folders = DriveApp.getFoldersByName(folderName);
    var folder = folders.hasNext() ? folders.next() : DriveApp.createFolder(folderName);
    
    var blob = Utilities.newBlob(Utilities.base64Decode(base64), mime, name);
    var file = folder.createFile(blob);
    file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    return file.getUrl();
  } catch(e) {
    return "[Upload Error]";
  }
}

function jsonResp(data) {
  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}

function formatDate(date) {
  if (!date) return "";
  var d = new Date(date);
  if (isNaN(d.getTime())) return date; // Already string?
  return Utilities.formatDate(d, Session.getScriptTimeZone(), "yyyy-MM-dd");
}
