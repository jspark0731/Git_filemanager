import React, { useState, useCallback, useEffect } from "react";
import { Modal, Button, Table, Tooltip, Input, message, Checkbox } from "antd";
import { PlusOutlined, RedoOutlined, DeleteOutlined, FileTextTwoTone, FolderTwoTone, EditOutlined, FolderOpenTwoTone } from "@ant-design/icons";
import { ColumnsType } from "antd/es/table";
import styled from "styled-components";
import { getFileSize } from "../../utils/number";
import { useQuery } from "@tanstack/react-query";
import path from "path";
import axios from 'axios';

const NameWrapper = styled.div`
  display: flex;
  align-items: center;
  cursor: pointer;
  gap: 6px;
`;
const ActionWrapper = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
`;

//파일 타입 받아오기 (폴더인지, 파일인지, (이건 깃 레포가 아닐 때)      언트랙인지, 모디파이드인지, 스테이징인지 커밋된건지 (이건 깃 레포일 때))
type FileType =  "folder" | "file";
type GitType = "null" | "untracked" | "modified" | "staged" | "committed" | "tracked" | "back";

type NameType = {
  fileName: string;
  type_file: FileType;
  type_git?: GitType;
};

interface FileTableDataType {
  key: React.Key;
  name: NameType;
  size: number;
  lastModified: string;
  action?: GitType;
}

const getFileIcon = (type1: FileType, type2?: GitType) => {
  switch (type1) {
    case "folder":
      switch (type2) {
        case "tracked":
          return <FolderTwoTone twoToneColor="#96F2D7" style={{ fontSize: 24 }} />;
        case "untracked":
          return <FolderTwoTone twoToneColor="#1677ff" style={{ fontSize: 24 }} />;
        case "null" :
          return <FolderTwoTone twoToneColor="lightgray" style={{ fontSize: 24 }} />;
        case "back" :
          return <FolderOpenTwoTone twoToneColor="lightgray" style={{ fontSize: 24 }} />;
        default:
          return <FolderTwoTone twoToneColor="lightgray" style={{ fontSize: 24 }} />;
      }

    case "file":
      switch (type2) {
        case "untracked":
          return <FileTextTwoTone twoToneColor="#1677ff" style={{ fontSize: 24 }} />;
        case "modified":
          return <FileTextTwoTone twoToneColor="#ff4d4f" style={{ fontSize: 24 }} />;
        case "staged":
          return <FileTextTwoTone twoToneColor="#f7f008" style={{ fontSize: 24 }} />;
        case "committed":
          return <FileTextTwoTone twoToneColor="#96F2D7" style={{ fontSize: 24 }} />;
        case "null" :
          return <FileTextTwoTone twoToneColor="lightgray" style={{ fontSize: 24 }} />;
        default:
          return <FileTextTwoTone twoToneColor="lightgray" style={{ fontSize: 24 }} />;
      }
  }
};


//실제 돌아갈 코드 부분
interface FileTableProps {
  path: string
  onPathChange: (newDir: string) => string;
}

//api 요청으로 백엔드에서 file list 호출
async function fetchFiles(path: string) {
  try {
    const encodedPath = encodeURIComponent(path);
    const response = await axios.get(`/api/root_files?path=${encodedPath}`, {
      withCredentials: true,
    });

    if (response.status !== 200 && response.status !== 304) {
      throw new Error(`API request failed with status ${response.status}`);
    }

    const data = response.data;

    if (!Array.isArray(data)) {
      throw new Error("Data is not an array");
    }

    console.log("Response data:", data);

    return data;
  } catch (error) {
    console.error("Error fetching files:", error);
    return [];
  }
}


export default function FileTable( { path, onPathChange }: FileTableProps) {
  const [tableHeight, setTableHeight] = useState<number>(0);
  const [fileList, setFileList] = useState<FileTableDataType[]>([]);

  const [isRenameModalVisible, setRenameModalVisible] = useState<boolean>(false);
  const [fileToRename, setFileToRename] = useState<NameType | null>(null);
  const [newName, setNewName] = useState<string>("");

  const [stagedFiles, setStagedFiles] = useState<FileTableDataType[]>([]);
  const [commitModalVisible, setCommitModalVisible] = useState<boolean>(false);


  const handleRenameClick = (record: FileTableDataType) => {
    setFileToRename(record.name);
    setRenameModalVisible(true);
  };


  const updateTableHeight = () => {
    const windowHeight = window.innerHeight;
    const desiredTableHeight = windowHeight - 300;
    setTableHeight(desiredTableHeight);
  };

  useEffect(() => {
    updateTableHeight();
    window.addEventListener("resize", updateTableHeight);

    return () => {
      window.removeEventListener("resize", updateTableHeight);
    };
  }, []);

  //파일 리스트 불러오기
  const fetchApi = useCallback(async (path: string) => {
    const data = await fetchFiles(path);
    console.log("path: " + path);
    const files = data.map((item: any) => ({
      key: item.key,
      name: {
        fileName: item.name,
        type_file: item.file_type,
        type_git: item.git_type,
      },
      size: item.size,
      lastModified: item.last_modified,
      action: item.git_type
    }));
  
    setFileList(files as FileTableDataType[]);
  
  // Push the current path to the backend
    await axios.post("/api/push_path", { path }, {
      headers: {
        "Content-Type": "application/json",
      },
      withCredentials: true
    });
  }, []);

  useEffect(() => {
    fetchApi(path);
  }, [fetchApi, path]);

  const [pathStack, setPathStack] = useState<string[]>([path]);


  //돌아가기
  const goBack = useCallback(() => {
    if (pathStack.length > 0) {
      const newPathStack = [...pathStack];
      newPathStack.pop();
      setPathStack(newPathStack);
      onPathChange(newPathStack[newPathStack.length - 1] || "");
    } else {
      console.log("No more paths in the stack");
    }
  }, [onPathChange, pathStack]);
  
  //
  const checkGitTypes = useCallback(() => {
    return fileList.every((file) => file.name.type_git === 'null');
  }, [fileList]);
  
  // git_init
  const initRepo = () => {
    const newPathStack = [...pathStack];
    setPathStack(newPathStack);
    const newPath = onPathChange(newPathStack[newPathStack.length - 1]);
    console.log("시시발  " + newPath);
  
    path = newPath;
    axios.post("/api/init_repo", { path: newPath.toString() }, {
      headers: {
        "Content-Type": "application/json",
      },
      withCredentials: true,
    })
    .then((response) => {
      if (response.data.message === "Repository initialized successfully") {
        message.success(response.data.message);
        console.log("Success!")
        fetchApi(path); // fetch the fileList again to update the UI
      } else {
        message.error(response.data.error);
      }
    })
    .catch((error) => {
      console.log("시발  " + path);
      console.error("Error initializing repository:", error);
      message.error("An error occurred while initializing the repository");
    });
  };
  
  

  
  // /api/git_add
async function gitAdd(filePath: string) {
  try {
    const response = await axios.post("/api/git_add", { path, file_path: filePath }, {
      headers: {
        "Content-Type": "application/json",
      },
      withCredentials: true,
    });

    if (response.status !== 200) {
      throw new Error(`API request failed with status ${response.status}`);
    }

    message.success("File added successfully");

    // Fetch the file list again to update the UI.
    fetchApi(path);
  } catch (error) {
    console.log("깃 add 시발  " + path);
    console.error("Error adding file:", error);
    message.error("An error occurred while adding the file");
  }
}

const getStagedFiles = useCallback(() => {
  const staged = fileList.filter(file => file.action === 'staged');
  setStagedFiles(staged);
}, [fileList]);

const handleCommit = async () => {
  try {
    const response = await axios.post("/api/commit", {
      path,
      commit_message: newName, // Assuming newName contains the commit message
      file_list: stagedFiles.map(file => file.name.fileName), // Extract file names from stagedFiles
    }, {
      headers: {
        "Content-Type": "application/json",
      },
      withCredentials: true,
    });

    if (response.status !== 200) {
      throw new Error(`API request failed with status ${response.status}`);
    }

    message.success("Files committed successfully");

    // Fetch the file list again to update the UI.
    fetchApi(path);
  } catch (error) {
    console.error("Error committing files:", error);
    message.error("An error occurred while committing the files");
  }
};

  

  const columns: ColumnsType<FileTableDataType> = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (value: NameType, record: FileTableDataType) => {
        if (!value) {
          return "";
        }
        const { fileName, type_file, type_git } = value;
        const normalizePath = (parts: string) => parts.replace(/\/+/g, '/');

        return (
          <NameWrapper onClick={() => {
            if (value.fileName === "..") {
              const newPath = path;
              console.log(newPath);
              goBack();
            } else if (type_file === "folder") {
              const newPath = normalizePath(`${path}/${record.name.fileName}`);
              if (!pathStack.includes(newPath)) {
                const newPathStack = [...pathStack, newPath];
                setPathStack(newPathStack);
                onPathChange(newPath);
              }
            }
          }}>
            {getFileIcon(type_file, type_git)}
            {fileName}
          </NameWrapper>
        );
      },
    },
    {
      title: "Size",
      dataIndex: "size",
      key: "size",
      render: (value) => {
        if (!value) {
          return "-";
        }
  
        return getFileSize(value);
      },
    },
    {
      title: "Modified Date",
      dataIndex: "lastModified",
      key: "lastModified",
    },
    {
      title: "Git Action",
      dataIndex: "action",
      key: "action",
      render: (value: GitType, record : FileTableDataType) => {
        if (!value) {
          return "";
        }
  
        switch (value) {
          case "untracked":
            return (
              <Tooltip title="Adding the file into a staging area">
                <Button type="primary" icon={<PlusOutlined />} onClick={() => gitAdd(record.name.fileName)}>
                  Add
                </Button>
              </Tooltip>
            );
  
          case "modified":
            return (
              <ActionWrapper>
                <Tooltip title="Adding the file into a staging area">
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => gitAdd(record.name.fileName)}>
                    Add
                  </Button>
                </Tooltip>
  
                <Tooltip title="Undoing the modification">
                  <Button icon={<RedoOutlined />}>
                    Restore
                  </Button>
                </Tooltip>
              </ActionWrapper>
            );
  
          case "staged":
            return (
              <ActionWrapper>
                <Tooltip title="Unstaging changes">
                  <Button icon={<RedoOutlined />}>
                    Restore
                  </Button>
                </Tooltip>
              </ActionWrapper>
            );
  
          case "committed":
            return (
              <ActionWrapper>
                <Tooltip title=" Untracking file">
                  <Button icon={<DeleteOutlined />} danger>
                    Untrake
                  </Button>
                </Tooltip>
  
                <Tooltip title="Deleting file">
                  <Button type="primary" icon={<DeleteOutlined />} danger>
                    Delete
                  </Button>
                </Tooltip>
                
                <Tooltip title="Renaming file">
                  <Button icon={<EditOutlined />} onClick={() => handleRenameClick(record)}>
                    Rename
                  </Button>
                </Tooltip>
              </ActionWrapper>
            );

          case "null" :
            return "";

          case "back" :
            return "";

          case "tracked" :
            return "";
        }
      },
    },
  ];


  return (
    <>
      {
        checkGitTypes() && 
        <Button 
          type="primary"
          onClick={initRepo}
        >
          Create Git Repo
        </Button>
      }

{
        !checkGitTypes() && 
        <Button 
          type="primary"
          onClick={() => {
            getStagedFiles();
            setCommitModalVisible(true);
          }}
        >
          Committing Staged Changes
        </Button>

      }

      <Table
        columns={columns}
        dataSource={fileList}
        pagination={false}
        scroll={{ y: tableHeight }}
      />

      <Modal
        title="Rename File"
        visible={isRenameModalVisible}
        onOk={async () => {
          // 백 실제 api랑 연결해야함.
          const newName = "newName"; // Get this value from your form.
          await axios.post(`/api/rename_file`, { 
            oldName: fileToRename?.fileName, 
            newName
          });

          // Fetch the file list again to update the UI.
          await fetchApi(path);

          // Close the modal.
          setRenameModalVisible(false);
          setFileToRename(null);
          setNewName(""); // Reset newName state
        }}
        onCancel={() => {
          setRenameModalVisible(false);
          setNewName(""); // Reset newName state
        }}
      >
        <Input
          placeholder="Enter new file name"
          value={newName}
          onChange={e => {
            setNewName(e.target.value);
          }}

        />
      </Modal>

      <Modal
        title="Commit Staged Changes"
        visible={commitModalVisible}
        onOk={handleCommit}
        onCancel={() => {
          setCommitModalVisible(false);
        }}
        okText="Commit"
      >
        {stagedFiles.map((file) => (
          <p key={file.key}>{file.name.fileName}</p>
        ))}

        <br />

        <Input
          placeholder="Enter commit message"
          value={newName}
          onChange={(e) => {
            setNewName(e.target.value);
          }}
        />
      </Modal>
    </>
  );
}