import React, { useState, useCallback, useEffect } from "react";
import { Modal, Button, Table, Tooltip } from "antd";
import { PlusOutlined, RedoOutlined, DeleteOutlined, FileTextTwoTone, FolderTwoTone, EditOutlined } from "@ant-design/icons";
import { ColumnsType } from "antd/es/table";
import styled from "styled-components";
import { getFileSize } from "../../utils/number";
import { useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

const NameWrapper = styled.div`
  display: flex;
  align-items: center;
  
  gap: 6px;
`;
const ActionWrapper = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
`;

//파일 타입 받아오기 (폴더인지, 파일인지, (이건 깃 레포가 아닐 때)      언트랙인지, 모디파이드인지, 스테이징인지 커밋된건지 (이건 깃 레포일 때))
type FileType =  "folder" | "file" | "untracked" | "modified" | "staged" | "committed";
type NameType = {
  fileName: string;
  type?: FileType;
};

interface FileTableDataType {
  key: React.Key;
  name: NameType;
  size: number;
  lastModified: string;
  action?: FileType;
}

const getFileIcon = (type: FileType) => {
  switch (type) {
    case "folder":
      return <FolderTwoTone twoToneColor = "lightgray" style = {{ fontSize: 24}}/>;
    case "file" :
      return <FileTextTwoTone twoToneColor="lightgray" style={{ fontSize: 24 }} />;
    case "untracked":
      return <FileTextTwoTone twoToneColor="#1677ff" style={{ fontSize: 24 }} />;
    case "modified":
      return <FileTextTwoTone twoToneColor="#ff4d4f" style={{ fontSize: 24 }} />;
    case "staged":
      return <FileTextTwoTone twoToneColor="#f7f008" style={{ fontSize: 24 }} />;
    case "committed":
      return <FileTextTwoTone twoToneColor="#96F2D7" style={{ fontSize: 24 }} />;
  }
};

const columns: ColumnsType<FileTableDataType> = [
  {
    title: "Name",
    dataIndex: "name",
    key: "name",
    render: (value: NameType) => {
      if (!value) {
        return "";
      }

      const { fileName, type } = value;

      return (
        <NameWrapper>
          {type && getFileIcon(type)}
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
    title: "Last modified",
    dataIndex: "lastModified",
    key: "lastModified",
  },
  {
    title: "Git Action",
    dataIndex: "action",
    key: "action",
    render: (value: FileType) => {
      if (!value) {
        return "";
      }

      switch (value) {
        case "untracked":
          return (
            <Tooltip title="Adding the file into a staging area">
              <Button type="primary" icon={<PlusOutlined />}>
                Add
              </Button>
            </Tooltip>
          );

        case "modified":
          return (
            <ActionWrapper>
              <Tooltip title="Adding the file into a staging area">
                <Button type="primary" icon={<PlusOutlined />}>
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
                <Button icon = {<EditOutlined />} >
                  Rename
                </Button>
              </Tooltip>
            </ActionWrapper>
          );
      }
    },
  },
];

interface FileTableProps {}

//api 요청으로 백엔드에서 file list 호출
async function fetchFiles() {
  try {
    const response = await fetch("/api/root_files?path=/C:/");

    if (!response.ok) {
      throw new Error(`API request failed with status ${response.status}`);
    }

    const data = await response.json();

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

export default function FileTable(props: FileTableProps) {
  const { pathname } = useLocation();
  const [fileList, setFileList] = useState<FileTableDataType[]>([]);

  const fetchApi = useCallback(async () => {
    const data = await fetchFiles();
    const files = data.map((item: any) => ({
      key: item.key,
      name: {
        fileName: item.name,
        type: item.type,
      },
      size: item.size,
      lastModified: item.last_modified,
    }));
  
    // 정렬된 key 값으로 새로운 배열을 생성하고 그 배열에 파일/폴더 데이터를 저장합니다.
    const sortedFiles = Array.from({ length: files.length }).map((_, index) => files.find((file: FileTableDataType) => file.key === index)).filter((file: FileTableDataType | undefined) => file !== undefined);
    setFileList(sortedFiles as FileTableDataType[]);
  }, [pathname]);    

  useEffect(() => {
    fetchApi();
  }, [fetchApi]);

  return (
    <Table
      columns={columns}
      dataSource={fileList}
      pagination={{
        current: 1,
        defaultCurrent: 1,
        pageSize: 10,
        defaultPageSize: 10,
        position: ["bottomCenter"],
      }}
    />
  );
}