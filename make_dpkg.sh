#!/bin/bash

# set -x
set -e

SCRIPT_DIR=$(dirname $(readlink -f $0))
WORK_DIR=$(mktemp -d)


mkdir -p ${WORK_DIR}/aiy-projects-python-0.1/opt/aiy/
git worktree add --detach ${WORK_DIR}/aiy-projects-python-0.1/debian origin/debian
git worktree add --detach ${WORK_DIR}/aiy-projects-python-0.1/projects-python origin/aiyprojects

# Copy aiyprojects and set remote to github.
AIY_PYTHON_DIR=${WORK_DIR}/aiy-projects-python-0.1/projects-python
rm -f ${AIY_PYTHON_DIR}/.git
if [ -d ${AIY_PYTHON_DIR}/.git ]; then
    rsync -rL --exclude=.git/shallow ${SCRIPT_DIR}/.git ${AIY_PYTHON_DIR}
else
    cp -r ${SCRIPT_DIR}/../.git/modules/aiy-projects-python ${AIY_PYTHON_DIR}/.git
fi
ls -la ${AIY_PYTHON_DIR}/.git/
sed -i '/\tworktree =/d' ${AIY_PYTHON_DIR}/.git/config
git -C ${AIY_PYTHON_DIR} checkout aiyprojects
for BRANCH in $(git -C ${AIY_PYTHON_DIR} branch | sed 's/\*//'); do
    if [[ "$BRANCH" != "aiyprojects" ]]; then
        git -C ${AIY_PYTHON_DIR} branch -D ${BRANCH}
    fi
done
git -C ${AIY_PYTHON_DIR} remote remove origin | true
git -C ${AIY_PYTHON_DIR} remote add origin \
    https://github.com/google/aiyprojects-raspbian

pushd ${WORK_DIR}/aiy-projects-python-0.1
tar cf ${WORK_DIR}/aiy-projects-python_0.1.orig.tar.xz projects-python
# tar tf ${WORK_DIR}/aiy-projects-python_0.1.orig.tar.xz
find .

debuild --no-lintian -us -uc

cp ${WORK_DIR}/aiy-projects-python_0.1-0_all.deb ${SCRIPT_DIR}
rm -rf ${WORK_DIR}
popd
git worktree prune
