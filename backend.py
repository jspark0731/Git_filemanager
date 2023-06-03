from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import unquote
from typing import List
from pydantic import BaseModel
from git import Repo, GitCommandError, InvalidGitRepositoryError, NULL_TREE
import os 
from typing import Optional
import locale
import datetime
import logging
import requests
from collections import deque

path_stack = deque()

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# 허용할 origin 주소들을 리스트로 입력합니다.(CORS setting)
origins = ["http://localhost", "http://localhost:3000", "http://localhost:8000", ...]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/frontend/static", StaticFiles(directory="frontend/build/static"), name="static")

class FileItem(BaseModel):
    key: Optional[int] = None
    name: Optional[str] = None
    file_type: Optional[str] = None
    git_type: Optional[str] = None
    size: Optional[float] = None  # float으로 변경(int 숫자 범위)
    last_modified: Optional[str] = None
    path: Optional[str] = None
    git_path: Optional[str] = None
    file_path : Optional[str] = None
    old_file_path : Optional[str] = None
    new_file_path : Optional[str] = None
    commit_message: Optional[str] = None
    file_paths: Optional[list[str]] = None

    https: str # cloning https
    username: str # username for private clone
    access_token: str # token for private clone


path_stack = deque() # path_stack 선언



def sort_key(item: FileItem) -> str:
    locale.setlocale(locale.LC_COLLATE, 'ko_KR.UTF-8')
    return locale.strxfrm(item.name)


@app.get("/api/root_files", response_model=List[FileItem])
async def get_files(path: str):
    path = unquote(path)
    path = os.path.normpath(path)

    # Log the normalized path
    #logging.info(f"Normalized path: {path}")

    try:
        #logging.info(f"Received path: {path}")
        directory = os.path.abspath(os.path.join("/", path))

        # Log the absolute directory path
        #logging.info(f"Absolute directory path: {directory}")

        if not os.path.exists(directory):
            raise HTTPException(status_code=404, detail="Directory not found")

        folders = []
        files = []

        # Add a special folder item for going back
        go_back_item = FileItem(key=-1, name="..", file_type="folder", git_type="null", size=0, last_modified="")

        # If the directory isn't the root directory, add the go_back_item
        if directory != "C:\\":
            folders.append(go_back_item)

        try:
            repo = Repo(directory, search_parent_directories=True)
            is_git = True
        except InvalidGitRepositoryError:
            is_git = False

        with os.scandir(directory) as entries:
            entries = [entry for entry in entries]
            entries.sort(key=lambda entry: (not entry.is_dir(), entry.name))

            for key, entry in enumerate(entries):
                file_type = "folder" if entry.is_dir() else "file"
                
            # Git_Type 인식 (코드 병합 부분) git_folder
                if is_git == True :
                    if file_type == "file" : 
                        diff_index = repo.index.diff(None)
                        diff_staged = repo.index.diff("HEAD")
                        full_path = os.path.relpath(entry.path, repo.working_tree_dir).replace("\\", "/")

                        #logging.info("{full_path}")
                        if full_path in repo.untracked_files:
                            git_type = "untracked"
                        elif full_path in [d.a_path for d in diff_staged]:
                            git_type = "staged"
                        elif full_path in [d.a_path for d in diff_index]:
                            git_type = "modified"
                        else:
                            git_type = "committed"
                            
                    if file_type == "folder":
                        folder_path = entry.path
                        folder_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
                        untracked_folder_files = [f for f in folder_files if os.path.relpath(f, repo.working_tree_dir).replace("\\", "/") in repo.untracked_files]
                        if len(folder_files) == len(untracked_folder_files):
                            git_type = "untracked"
                        else : 
                            git_type = "tracked"


                elif is_git == False and file_type == "folder":
                    git_type = "null"

                elif is_git == False and file_type == "file" :
                    git_type = "null"
                    
                else:
                    git_type = "null"

                directory = os.path.abspath(os.path.join("/", path))


                file_size = entry.stat().st_size
                last_modified = datetime.datetime.fromtimestamp(
                    entry.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                item = FileItem(key=key, name=entry.name, file_type=file_type,git_type=git_type, size=file_size, last_modified=last_modified)
                
                if file_type == "folder":
                    folders.append(item)
                else:
                    files.append(item)

        return folders + files
    
    except Exception as e:
        #logging.error(f"Error occurred: {str(e)}")  # 로깅 레벨을 error로 설정
        raise HTTPException(status_code=500, detail=str(e))


# push path_stack
@app.post("/api/push_path")
async def push_path(path: FileItem):
    path_stack.append(path.path)
    logging.info(f"Path_Stack: {path_stack}")   # path_stack에 push 잘 되나 출력.
    return {"message": "Path pushed successfully"}


# path_reset
@app.post("/api/reset_path_stack")
async def reset_path_stack():
    path_stack.clear()  # 새로 고침하면 path_stack 초기화
    return {"message": "Path stack reset successfully"}


@app.post("/api/init_repo")
async def init_repo(repo_path: FileItem):
    path_str = repo_path.path
    #logging.info(f"INIT_PATH: {path_str}")

    if path_str == "C:/":
        raise HTTPException(status_code=400, detail="Cannot initialize repository in root directory")

    try:
        #logging.info(f"try문 로깅: {path_str}")
        # Initialize the directory as a git repository
        repo = Repo.init(path_str)
        # Create an empty commit
        repo.index.commit("Initial commit") #Ref 'HEAD' did not resolve to an object 오류 해결
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Repository initialized successfully"}

# git_add
@app.post("/api/git_add")
async def git_add(request: FileItem):
    git_path = request.git_path
    file_path = request.file_path

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")

    # Try to add the file
    try:
        repo.git.add(file_path)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "File added successfully"}


# git_restore_staged
@app.post("/api/git_restore_staged")
async def git_restore(request: FileItem):
    git_path = request.git_path
    file_path = request.file_path

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")

    # Try to restore the file
    try:
        repo.git.restore("--staged", file_path)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "File restored successfully"}



#git_undomodify
@app.post("/api/git_undo_modify")
async def git_undo_modify(request: FileItem):
    git_path = request.git_path
    file_path = request.file_path

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")

    # Try to undo the modification
    try:
        repo.git.restore(file_path)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Undone Modification successfully"}


#git_rm --cached
@app.post("/api/git_remove_cached")
async def git_remove(request: FileItem):
    git_path = request.git_path
    file_path = request.file_path

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")

    # Try to remove the file from the index
    try:
        repo.git.rm("--cached", file_path)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "File removed from index successfully"}


#git_rm
@app.post("/api/git_remove")
async def git_remove(request: FileItem):
    git_path = request.git_path
    file_path = request.file_path

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")

    # Try to remove the file
    try:
        repo.git.rm(file_path)
        repo.index.commit("Remove file from index")
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "File removed successfully"}


#git_mv
@app.post("/api/git_move")
async def git_rename(request: FileItem):
    git_path = request.git_path
    old_file_path = request.old_file_path
    new_file_path = request.new_file_path

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")

    # Try to move the file
    try:
        repo.git.mv(old_file_path, new_file_path)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "File renamed successfully"}


#git_commit
@app.post("/api/git_commit")
async def git_commit(request: FileItem):
    git_path = request.git_path
    commit_message = request.commit_message
    file_paths = request.file_paths

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")

    # Add files to staging area
    for file_path in file_paths:
        try:
            logging.info(f"committed path: {file_path}")
            repo.git.add(file_path)
        except GitCommandError as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Commit changes
    try:
        repo.index.commit(commit_message)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Files committed successfully"}


@app.post("/api/get_staged_files")
async def get_staged_files(repo_path: FileItem):
    path_str = repo_path.path
    #logging.info(f"GET_STAGED_FILES_PATH: {path_str}")

    try:
        repo = Repo(path_str)
        staged_files = []
        for item in repo.index.diff("HEAD"):
            file_path = os.path.join(path_str, item.a_path)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                last_modified = datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                staged_files.append({
                    'key': len(staged_files),
                    'name': item.a_path,
                    'file_type': 'file',
                    'git_type': 'staged',
                    'size': file_size,
                    'last_modified': last_modified
                })

        return {"files": staged_files}

    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Staged files fetched successfully"}


@app.post("/api/git_root_path")
async def get_git_root_path(item: FileItem):
    try:
        repo = Repo(item.path, search_parent_directories=True)
        git_root_path = repo.git.rev_parse("--show-toplevel")
        return {"git_root_path": git_root_path}
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")


@app.get("/{path:path}", include_in_schema=False)
async def catch_all(path: str):
    return FileResponse("frontend/build/index.html")


@app.get("/")
async def read_root():
    return FileResponse("frontend/build/index.html")


# branch API from here

class BranchGetRequest(BaseModel):
    git_path: str

@app.get("/api/branches")
async def get_branches(request: BranchGetRequest):
    git_path = request.git_path

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")
    
    branches = [branch.name for branch in repo.branches]
    
    if branches:
        return {"branches": branches} 
    else:
        raise HTTPException(status_code=400, detail="Branch already exists")
    

class BranchRequest(BaseModel):  
    git_path: str
    branch_name: str

@app.post("/api/branch_create")
async def branch_create(request: BranchRequest):
    git_path = request.git_path
    branch_name = request.branch_name

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")
    
    # Check if the branch already exists
    if any(branch_name == branch.name for branch in repo.branches):
        raise HTTPException(status_code=400, detail="Branch already exists")

    # Try to create new branch
    try:
        repo.create_head(branch_name)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Branch created successfully"}


@app.post("/api/branch_delete")
async def branch_delete(request: BranchRequest):
    git_path = request.git_path
    branch_name = request.branch_name

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")
    
    # Check if the branch already exists
    if not any(branch_name == branch.name for branch in repo.branches):
        raise HTTPException(status_code=400, detail="Branch doesn't exists")

    # Try to delete new branch
    try:
        repo.delete_head(branch_name)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Branch deleted successfully"}


class BranchRenameRequest(BaseModel):  
    git_path: str
    old_name: str
    new_name: str

@app.post("/api/branch_rename")
async def branch_rename(request: BranchRenameRequest):
    git_path = request.git_path
    old_name = request.old_name
    new_name = request.new_name

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")
    
    # Check if the branch already exists
    if not any(old_name == branch.name for branch in repo.branches):
        raise HTTPException(status_code=400, detail="Branch doesn't exists")
    
    # Check if new name already exists
    if any(new_name == branch.name for branch in repo.branches):
        raise HTTPException(status_code=400, detail="Branch already exists")    

    # Try to rename new branch
    try:
        repo.heads[old_name].rename(new_name)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Branch renamed successfully"}


@app.post("/api/branch_checkout")
async def branch_checkout(request: BranchRequest):
    git_path = request.git_path
    branch_name = request.branch_name

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")
    
    # Check if the branch already exists
    if not any(branch_name == branch.name for branch in repo.branches):
        raise HTTPException(status_code=400, detail="Branch doesn't exists")
    
    #check if the branch is current branch
    if branch_name == repo.active_branch.name:
        raise HTTPException(status_code=400, detail=f"Already on {branch_name}")

    # Try to checkout branch
    try:
        repo.git.checkout(branch_name)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Branch checkouted successfully"}



# merge API from here
@app.post("/api/branch_merge")
async def branch_merge(request: BranchRequest):
    git_path = request.git_path
    branch_name = request.branch_name   # target

    # Check if the path is a valid directory
    if not os.path.exists(git_path) or not os.path.isdir(git_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        repo = Repo(git_path)
    except InvalidGitRepositoryError:
        raise HTTPException(status_code=400, detail="The directory is not a valid git repository")

    # Check if there are uncommitted changes
    if repo.is_dirty():
        raise HTTPException(status_code=400, detail="Uncommitted changes exist")

    # Try to merge
    try:
        repo.git.merge(branch_name)
    except GitCommandError:       
        unmerged_paths = []
        for entry in repo.index.entries.values():
        # add file name that has conflicts
            if entry.stage != 0 and entry.path not in unmerged_paths:
                unmerged_paths.append(entry.path)    
        repo.git.merge("--abort")
        raise HTTPException(status_code=500, detail="Merge failed", headers=unmerged_paths)    

    return {"message": "Branch merged successfully"}

# for Feature_3

@app.get("api/git_history")
async def get_git_history(request: GitItem):
    git_path = request.repoPath
    # branch_name = request.branch_name ( if sorting by selected branch for graph )

    try:
        repo = Repo(git_path)

        # all branch & creation time
        commits = list(repo.iter_commits())

        history_list = []

        for commit in commits:

            branch_names = [branch.name for branch in repo.branches if commit in repo.iter_commits(branch)]
            
            # we may need more information about commit for making history tree
            commit_info = {
                'commit_checksum': commit.hexsha, # string type
                'parent_checksums': [parent.hexsha for parent in commit.parents],
                'commit_message': commit.message, 
                'branches': branch_names,
                'author': commit.author.name, # string type
                #'date': datetime.datetime.fromtimestamp(
                #    commit.authored_datetime).strftime("%Y-%m-%d %H:%M:%S")
            }
            history_list.apeend(commit_info)
        
        return history_list
    
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

# git_history will get git_root_path

# repo.iter_commits() : all commit travels and get commit
# > travel commits in order of creation date
# repo.iter_commits('branch_name') : travel commits in branch_name

# Commit object has these informations
# hexsha : commit checksum
# message : commit message
# author : commit author ( Actor object : name & e-mail )
# committed_date : commit date ( unix timestamp )
# parents : parent commits => Commit object list
# tree : tree of commit ( Tree object )

# about commit.parents ( usually commits have one parents but in merge.. )
# if the commit created by merge.. first: mainline , second..: merged last commit

# basic history list has commits in order of creation time
# each commits have basic information for drawing history tree
# > checksum / parent's checksums / branches / author.name / (commit date)


@app.get("/api/commit_information")
async def get_commit_information(request:GitItem):
    git_path = request.repoPath

    try:
        repo = Repo(git_path)

        try:
            commit = repo.commit(request.commit_checksum)
        except:
            raise HTTPException(status_code=404, detail="Commit not found")
        
        commit_info = {
            'commit_checksum': commit.hexsha,
            'parent_checksums': [parent.hexsha for parent in commit.parents],
            'author': commit.author.name,
            'commiter': commit.committer.name,
            'date': datetime.datetime.fromtimestamp(
                commit.authored_datetime).strftime("%Y-%m-%d %H:%M:%S")
        }

        return commit_info

# Feature 4

@app.post("/api/public_clone")
async def public_clone(request: GitItem):
    path = request.path
    clone_link = request.https

    try:
        Repo.clone_from(clone_link, path)

        return {"message": "Clone Successfully"}

    
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

# commit's detail informaion
# > commit checksum / parent_checksums / author / commiter / date
# this api does not have changed data for files


@app.get("/api/changed_files")
def get_changed_files(request: GitItem):
    git_path = request.repoPath

    try:
        repo = Repo(git_path)

        try:
            commit = repo.commit(request.commit_checksum)
        except:
            raise HTTPException(status_code=404, detail="Commit not found")
        
        changed_files = []

        if commit.parents:
            diff_index = commit.parents[0].diff(commit)
        else:
            diff_index = commit.diff(NULL_TREE)
        
        # it recognize type only A / D / M
        for diff in diff_index:
            if diff.change_type == 'A':
                changed_files.append({
                    "file_name": os.path.basename(diff.b_path),
                    "change_type": "added"
                })
            elif diff.change_type == 'D':
                changed_files.append({
                    "file_name": os.path.basename(diff.a_path),
                    "change_type": "deleted"
                })
            elif diff.change_type == 'M':
                changed_files.append({
                    "file_name": os.path.basename(diff.a_path),
                    "change_type": "modified"
                })

        return changed_files
    
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

# this api recognize files in type added / removed / modified
# but we can think the file type renamed ( copy ? )

# changed files have elements > ('file_name', 'change_type')

# this api also only recognize mainline branch
# but we can choose branch and parameter branch or parent checksum
# if get branch > branch and parent checksum matching 
# if get parent checksum > if not initial commit, we can replace it


@app.get("/api/changed_data")
def get_changed_data(request: GitItem):
    git_path = request.repoPath
    file_path = request.path

    try:
        repo = Repo(git_path)

        try:
            commit = repo.commit(request.commit_checksum)
        except:
            raise HTTPException(status_code=404, detail="Commit not found")
        
        if commit.parents:
             diff_index = commit.parents[0].diff(commit)
        else:
            diff_index = commit.diff(NULL_TREE)
        
        diff_info = []

        # get path about git root repository
        path = os.path.relpath(file_path, repo.working_tree_dir).replace("\\", "/")
        for diff in diff_index:
            if diff.a_path == path or diff.b_path == path:
                diff_info.append({
                    'change_type': diff.change_type,
                    "added_lines": diff.b_blob.data_stream.read().decode().split("\n") if diff.b_blob is not None else [],
                    "removed_lines": diff.a_blob.data_stream.read().decode().split("\n") if diff.a_blob is not None else [],
                })
        
        if not diff_info:
            raise HTTPException(status_code=404, detail="File not found in the commit")
        
        return diff_info
    
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

# parameter : repoPath and filePath

# commit.diff(NULL_TREE) is for first commit >> all codes are changes
# first commit : a_path == None

# a_path : file path for parent commit & b_path : file path for current commit

# change_type: 'A' : add & 'D' : remove & 'M' : modified & 'R' : renamed & 'C' : copy
# line changes : before changes > removed_lines & after changes > added_lines
# add_lines and removed_lines are list for change strings

# this api show information based on main line branch
# so, if you see changed information based on merged branch
# > we can change diff_index = commit.parents[0].diff(commit)
# > to diff_index = commit.parents[1 or 2 ...].diff(commit)

# this case, parameter need commit_checksum > checksum == commit.parents[0] or not

# we must have more error handling codes

# Repo.clone(url, path)
# > clone in url to path


@app.get("/api/repo_status")
async def get_repo_status(request: GitItem):
    clone_link = request.https
    access_token = request.access_token

    headers = {
        'Authorization': f'token {access_token}',
    }

    try:
        response = requests.get(clone_link, headers = headers)

        if response.status_code == 200:
            return {'public': response.json()["private"] == False}
        elif response.status_code == 404:
            return {'error': 'Repository does not exist or not access have'}
        else:
            return {'error': 'Error occured'}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# for this api, we need to import requests >> install

# to access git repository and get private or public,
# this api need access_token early

# if repo is public, 'public': 'True' / if repo is private, 'public': 'False'
# if repo does not exist or does not have access : status_code == 404


@app.post("/api/private_clone")
async def private_clone(request: GitItem):
    path = request.path
    clone_link = request.https
    username = request.username
    access_token = request.access_token

    try:
        os.environ['GIT_ASKPASS'] = 'echo'
        os.environ['TOKEN'] = access_token

        Repo.clone_from(clone_link, path)

        return {"message": "Clone Successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# for private clone
# basic https >> need id and Access token
